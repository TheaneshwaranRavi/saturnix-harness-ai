from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from saturnix_harness.agents.base import AgentRuntime
from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.core.agent_constructor import AgentConstructor
from saturnix_harness.core.improvement_engine import RecursiveImprovementEngine
from saturnix_harness.core.intent_mapper import HumanIntentMapper
from saturnix_harness.core.verification_engine import VerificationEngine
from saturnix_harness.core.workflow import NavigationWorkflowBuilder
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.monitoring.events import MonitoringLayer
from saturnix_harness.schemas import (
    BrainName,
    BrainRouteRequest,
    ExecutionTrace,
    HarnessRequest,
    SaturnixExecutionRequest,
    SaturnixExecutionResult,
    ToolCall,
    WorkflowPlan,
    WorkflowStep,
)
from saturnix_harness.tools.router import ToolRouter

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """E: Execution Engine."""

    def __init__(
        self,
        agents: dict[str, AgentRuntime],
        tool_router: ToolRouter,
        memory: MemoryManager,
    ) -> None:
        self.agents = agents
        self.tool_router = tool_router
        self.memory = memory

    async def execute(self, plan: WorkflowPlan) -> tuple[str, list[ExecutionTrace]]:
        outputs: dict[str, Any] = {}
        traces: list[ExecutionTrace] = []
        for step in plan.steps:
            trace = ExecutionTrace(step_id=step.id, step_name=step.name, ok=False)
            try:
                output, provider = await self._execute_step(step, outputs)
                outputs[step.id] = output
                trace.ok = True
                trace.output = output
                trace.provider = provider
            except Exception as exc:
                trace.ok = False
                trace.error = str(exc)
                outputs[step.id] = f"Step failed: {exc}"
            finally:
                trace.completed_at = datetime.now(timezone.utc)
                traces.append(trace)
        final_output = str(next(reversed(outputs.values()), ""))
        return final_output, traces

    async def _execute_step(self, step: WorkflowStep, outputs: dict[str, Any]):
        context = "\n\n".join(
            str(outputs[dependency])
            for dependency in step.depends_on
            if dependency in outputs
        )
        if step.action == "brain":
            if not step.agent_name or step.agent_name not in self.agents:
                raise ValueError(f"No agent runtime found for step: {step.name}")
            response = await self.agents[step.agent_name].run(step.prompt or "", context=context)
            return response.content, response.provider
        if step.action == "tool":
            result = await self.tool_router.execute(step.tool_call or ToolCall(name="echo"))
            return result.output, None
        if step.action == "memory_write":
            record = self.memory.remember(
                content=step.prompt or "",
                namespace=step.metadata.get("namespace", "default"),
                kind=step.metadata.get("kind", "workflow_note"),
            )
            return record.model_dump(), None
        if step.action == "memory_search":
            records = self.memory.recall(
                query=step.prompt or "",
                namespace=step.metadata.get("namespace", "default"),
                limit=step.metadata.get("limit", 5),
            )
            return [record.model_dump() for record in records], None
        raise ValueError(f"Unsupported step action: {step.action}")


class SaturnixExecutionEngine:
    """High-level SATURNIX execution engine.

    This engine owns the complete E-step lifecycle:

    1. receive user goal
    2. call intent mapper
    3. call brain router
    4. construct required agents
    5. create workflow plan
    6. execute steps
    7. validate output
    8. save memory
    9. return final structured result
    """

    def __init__(
        self,
        intent_mapper: HumanIntentMapper,
        brain_router: BrainRouter,
        agent_constructor: AgentConstructor,
        workflow_builder: NavigationWorkflowBuilder,
        verifier: VerificationEngine,
        tool_router: ToolRouter,
        memory: MemoryManager,
        monitoring: MonitoringLayer | None = None,
    ) -> None:
        self.intent_mapper = intent_mapper
        self.brain_router = brain_router
        self.agent_constructor = agent_constructor
        self.workflow_builder = workflow_builder
        self.verifier = verifier
        self.tool_router = tool_router
        self.memory = memory
        self.monitoring = monitoring or MonitoringLayer()
        self.improvement_engine = RecursiveImprovementEngine(memory)

    async def execute_goal(self, request: SaturnixExecutionRequest) -> SaturnixExecutionResult:
        self.monitoring.record(
            name="execution.started",
            message="SATURNIX execution engine started.",
            metadata={"goal": request.goal},
        )
        logger.info("SATURNIX execution started for goal: %s", request.goal)

        try:
            harness_request = HarnessRequest(
                goal=request.goal,
                input=request.input,
                local_only=request.local_only,
                auto_improve=request.auto_improve,
                metadata=request.metadata,
            )
            intent = self.intent_mapper.map(harness_request)
            brain_route_request = BrainRouteRequest(
                task=request.goal,
                task_type=request.task_type or intent.domain,
                privacy_level=_privacy_level(request, intent.local_only),
                speed_priority=request.speed_priority,
                context_size=request.context_size,
                output_format=request.output_format,
            )
            brain_routing = self.brain_router.route_task(brain_route_request)
            preferred_brain = _preferred_brain_from_route(brain_routing.selected_brain)

            agents = self.agent_constructor.construct_for_intent(
                intent,
                preferred_brain=preferred_brain,
            )
            plan = self.workflow_builder.build(intent, agents, input_text=request.input)
            runtimes = self.agent_constructor.runtime_map(agents)
            step_engine = ExecutionEngine(
                agents=runtimes,
                tool_router=self.tool_router,
                memory=self.memory,
            )
            output, traces = await step_engine.execute(plan)
            validation = await self.verifier.verify(intent, output)

            if request.auto_improve and not validation.ok:
                logger.info("Validation failed; attempting SATURNIX improvement loop.")
                improved = await self.verifier.improve(intent, output, validation)
                validation.improved_output = improved
                output = improved
                validation = await self.verifier.verify(intent, output)
                validation.improved_output = improved

            memory_record = self.memory.remember(
                content=output,
                namespace="saturnix:execution",
                kind="execution_result",
                metadata={
                    "goal": request.goal,
                    "detected_intent": intent.summary,
                    "selected_brain": brain_routing.selected_brain,
                    "validation_ok": validation.ok,
                    "validation_score": validation.score,
                },
            )
            agents_used = [agent.name for agent in agents]
            workflow = [step.model_dump(mode="json") for step in plan.steps]
            execution_result = {
                "ok": all(trace.ok for trace in traces),
                "output": output,
                "traces": [trace.model_dump(mode="json") for trace in traces],
            }
            validation_result = validation.model_dump(mode="json")
            phase1_ids = self.memory.save_phase1_execution(
                goal=request.goal,
                detected_intent=intent.summary,
                agents_used=agents_used,
                brain_routing=brain_routing.model_dump(mode="json"),
                workflow=workflow,
                execution_result=execution_result,
                validation_result=validation_result,
            )
            memory_saved = memory_record.model_dump(mode="json")
            memory_saved["phase1_tables"] = phase1_ids
            result = SaturnixExecutionResult(
                goal=request.goal,
                detected_intent=intent.summary,
                agents_used=agents_used,
                brain_routing=brain_routing.model_dump(mode="json"),
                workflow=workflow,
                execution_result=execution_result,
                validation_result=validation_result,
                memory_saved=memory_saved,
                next_actions=_next_actions(validation.ok, validation.findings),
            )
            improvement = self.improvement_engine.analyze_execution(result)
            result.execution_result["recursive_improvement"] = improvement.model_dump(
                mode="json"
            )
            result.memory_saved["recursive_improvement_strategy_ids"] = (
                improvement.stored_strategy_ids
            )
            self.monitoring.record(
                name="execution.completed",
                message="SATURNIX execution engine completed.",
                metadata={
                    "goal": request.goal,
                    "selected_brain": brain_routing.selected_brain,
                    "validation_ok": validation.ok,
                },
            )
            return result
        except Exception as exc:
            logger.exception("SATURNIX execution failed for goal: %s", request.goal)
            self.monitoring.record(
                name="execution.failed",
                message=str(exc),
                level="error",
                metadata={"goal": request.goal},
            )
            failure_result = SaturnixExecutionResult(
                goal=request.goal,
                detected_intent="",
                agents_used=[],
                brain_routing={},
                workflow=[],
                execution_result={
                    "ok": False,
                    "output": None,
                    "error": str(exc),
                    "traces": [],
                },
                validation_result={
                    "ok": False,
                    "score": 0.0,
                    "findings": [f"Execution failed before validation: {exc}"],
                    "improved_output": None,
                },
                memory_saved={},
                next_actions=[
                    "Inspect execution_result.error.",
                    "Check configuration, available brains, required tools, and input "
                    "completeness.",
                    "Retry with a narrower goal or explicit task_type/privacy/output_format "
                    "values.",
                ],
            )
            improvement = self.improvement_engine.analyze_execution(failure_result)
            failure_result.execution_result["recursive_improvement"] = (
                improvement.model_dump(mode="json")
            )
            failure_result.memory_saved["recursive_improvement_strategy_ids"] = (
                improvement.stored_strategy_ids
            )
            return failure_result


def _privacy_level(request: SaturnixExecutionRequest, intent_local_only: bool) -> str:
    if request.local_only or intent_local_only:
        return "local"
    return request.privacy_level


def _preferred_brain_from_route(selected_brain: str) -> BrainName | None:
    normalized = selected_brain.lower()
    if "claude" in normalized:
        return BrainName.claude
    if "gemini" in normalized:
        return BrainName.gemini
    if "groq" in normalized:
        return BrainName.groq
    if "minimax" in normalized or "coding via ollama" in normalized:
        return BrainName.ollama_coding
    if "gemma" in normalized or "ollama" in normalized:
        return BrainName.ollama_gemma
    if "gpt" in normalized:
        return BrainName.openai
    return None


def _next_actions(validation_ok: bool, findings: list[str]) -> list[str]:
    if validation_ok:
        return [
            "Review the execution result.",
            "Promote useful output or decisions into long-term memory if needed.",
            "Run a follow-up workflow for implementation, automation, or deeper verification.",
        ]
    actions = ["Review validation findings and rerun with clarified constraints."]
    actions.extend(f"Address finding: {finding}" for finding in findings[:3])
    actions.append("Use the fallback brain or reduce workflow scope if the issue persists.")
    return actions
