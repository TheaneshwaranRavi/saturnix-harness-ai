from __future__ import annotations

import json
import logging
from typing import Any

from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.core.agent_constructor import AgentConstructor
from saturnix_harness.core.cognitive_workflow_planner import CognitiveWorkflowPlanner
from saturnix_harness.core.consensus_engine import ConsensusEngine
from saturnix_harness.core.distributed_intelligence import DistributedIntelligenceEngine
from saturnix_harness.core.execution_engine import SaturnixExecutionEngine
from saturnix_harness.core.improvement_engine import RecursiveImprovementEngine
from saturnix_harness.core.intent_mapper import HumanIntentMapper
from saturnix_harness.core.security_sentinel import SecuritySentinel
from saturnix_harness.core.self_healing_infrastructure import (
    SelfHealingInfrastructureEngine,
)
from saturnix_harness.memory.neural_engine import NeuralMemoryEngine
from saturnix_harness.monitoring.events import MonitoringLayer
from saturnix_harness.schemas import (
    AutonomousAgentConstructionRequest,
    BrainRouteRequest,
    CognitiveWorkflowPlanRequest,
    ConsensusRequest,
    DistributedIntelligenceRequest,
    HarnessRequest,
    NeuralMemoryStoreRequest,
    OmegaRunRequest,
    OmegaRunResult,
    SaturnixExecutionRequest,
    SaturnixExecutionResult,
    SecurityScanRequest,
    SelfHealingInfrastructureRequest,
    ToolRoutingRequest,
)
from saturnix_harness.tools.intelligence_router import ToolIntelligenceRouter

logger = logging.getLogger(__name__)


class OmegaEngine:
    """SATURNIX-HARNESS OMEGA cognitive operating layer.

    OMEGA coordinates the framework's modular engines into a single autonomous
    cognitive loop: intent, agents, brains, tools, workflows, execution,
    verification, recursive improvement, memory, infrastructure, and evolution.
    """

    def __init__(
        self,
        intent_mapper: HumanIntentMapper,
        brain_router: BrainRouter,
        tool_intelligence_router: ToolIntelligenceRouter,
        agent_constructor: AgentConstructor,
        workflow_planner: CognitiveWorkflowPlanner,
        consensus_engine: ConsensusEngine,
        execution_engine: SaturnixExecutionEngine,
        improvement_engine: RecursiveImprovementEngine,
        neural_memory_engine: NeuralMemoryEngine,
        distributed_engine: DistributedIntelligenceEngine,
        self_healing_engine: SelfHealingInfrastructureEngine,
        security_sentinel: SecuritySentinel,
        monitoring: MonitoringLayer,
    ) -> None:
        self.intent_mapper = intent_mapper
        self.brain_router = brain_router
        self.tool_intelligence_router = tool_intelligence_router
        self.agent_constructor = agent_constructor
        self.workflow_planner = workflow_planner
        self.consensus_engine = consensus_engine
        self.execution_engine = execution_engine
        self.improvement_engine = improvement_engine
        self.neural_memory_engine = neural_memory_engine
        self.distributed_engine = distributed_engine
        self.self_healing_engine = self_healing_engine
        self.security_sentinel = security_sentinel
        self.monitoring = monitoring

    async def run(self, request: OmegaRunRequest) -> OmegaRunResult:
        self.monitoring.record(
            name="omega.started",
            message="SATURNIX-HARNESS OMEGA run started.",
            metadata={"goal": request.goal, "execute": request.execute},
        )
        intent = self.intent_mapper.map(
            HarnessRequest(
                goal=request.goal,
                input=request.input,
                local_only=request.local_only,
                auto_improve=request.auto_improve,
                metadata=request.metadata,
            )
        )
        brain_route = self.brain_router.route_task(
            BrainRouteRequest(
                task=request.goal,
                task_type=request.task_type or intent.domain,
                privacy_level=_privacy_level(request, intent.local_only),
                speed_priority=request.speed_priority,
                context_size=request.context_size,
                output_format=request.output_format,
            )
        )
        tool_route = self.tool_intelligence_router.route(
            ToolRoutingRequest(
                task=request.goal,
                task_type=request.task_type or intent.domain,
                speed_requirement=request.speed_priority,
                privacy_level=_privacy_level(request, intent.local_only),
                execution_cost="balanced",
                reliability_requirement="high",
                scalability_requirement="high",
                constraints=intent.constraints,
            )
        )
        agents = self.agent_constructor.construct_autonomous(
            AutonomousAgentConstructionRequest(
                task=request.goal,
                task_type=request.task_type or intent.domain,
                privacy_level=_privacy_level(request, intent.local_only),
                speed_priority=request.speed_priority,
                context_size=request.context_size,
                output_format=request.output_format,
                required_tools=tool_route.selected_tools,
                memory_needs=["long_term_memory", "execution_history"],
                max_agents=request.max_agents,
                metadata={"omega": True, **request.metadata},
            )
        )
        workflow_plan = self.workflow_planner.plan(
            CognitiveWorkflowPlanRequest(
                goal=request.goal,
                context=request.input,
                task_type=request.task_type or intent.domain,
                privacy_level=_privacy_level(request, intent.local_only),
                speed_priority=request.speed_priority,
                output_format=request.output_format,
                constraints=intent.constraints,
                required_tools=tool_route.selected_tools,
                persist_plan=request.persist_memory,
            )
        )
        security_scan = self.security_sentinel.scan(
            SecurityScanRequest(
                task=request.goal,
                workflow=workflow_plan.execution_graph.get("nodes", []),
                actions=tool_route.selected_tools,
                sensitivity_level=_privacy_level(request, intent.local_only),
            )
        )
        consensus = await self._maybe_consensus(request, intent.summary)
        execution = await self._maybe_execute(request)
        verification_result = _verification_from_execution(execution)
        improvement = self.improvement_engine.analyze_execution(execution)
        infrastructure = self._infrastructure_optimization(
            request=request,
            selected_tools=tool_route.selected_tools,
            execution=execution,
        )
        memory = self._persist_omega_memory(
            request=request,
            intent_summary=intent.summary,
            brain_route=brain_route.model_dump(mode="json"),
            agents=agents.model_dump(mode="json"),
            workflow=workflow_plan.model_dump(mode="json"),
            execution=execution.model_dump(mode="json"),
        )
        result = OmegaRunResult(
            goal=request.goal,
            detected_intent=intent.model_dump(mode="json"),
            autonomous_agents=agents.model_dump(mode="json"),
            brain_routing=brain_route.model_dump(mode="json"),
            tool_routing=tool_route.model_dump(mode="json"),
            workflow_plan=workflow_plan.model_dump(mode="json"),
            security_scan=security_scan.model_dump(mode="json"),
            consensus=consensus,
            execution_result=execution.execution_result,
            verification_result=verification_result,
            recursive_improvement=improvement.model_dump(mode="json"),
            long_term_memory=memory,
            infrastructure_optimization=infrastructure,
            evolution_plan=_evolution_plan(
                request=request,
                security_findings=security_scan.risks_detected,
                validation_findings=execution.validation_result.get("findings", []),
                infrastructure=infrastructure,
            ),
            next_actions=_next_actions(
                execution=execution,
                security_findings=security_scan.risks_detected,
                memory=memory,
            ),
        )
        self.monitoring.record(
            name="omega.completed",
            message="SATURNIX-HARNESS OMEGA run completed.",
            metadata={
                "goal": request.goal,
                "verification_ok": verification_result.get("ok"),
                "memory_saved": bool(memory),
            },
        )
        return result

    async def _maybe_consensus(
        self,
        request: OmegaRunRequest,
        intent_summary: str,
    ) -> dict[str, Any] | None:
        if not request.use_consensus:
            return None
        consensus = await self.consensus_engine.run_consensus(
            ConsensusRequest(
                task=request.goal,
                context=request.input or intent_summary,
                task_type=request.task_type or "omega orchestration",
                privacy_level=_privacy_level_from_request(request),
                output_format=request.output_format,
                min_brains=1,
                max_brains=3,
                include_local=True,
                max_tokens=512,
            )
        )
        return consensus.model_dump(mode="json")

    async def _maybe_execute(self, request: OmegaRunRequest) -> SaturnixExecutionResult:
        if request.execute:
            return await self.execution_engine.execute_goal(
                SaturnixExecutionRequest(
                    goal=request.goal,
                    input=request.input,
                    task_type=request.task_type,
                    privacy_level=request.privacy_level,
                    speed_priority=request.speed_priority,
                    context_size=request.context_size,
                    output_format=request.output_format,
                    local_only=request.local_only,
                    auto_improve=request.auto_improve,
                    metadata={"omega": True, **request.metadata},
                )
            )
        return SaturnixExecutionResult(
            goal=request.goal,
            detected_intent="planned_only",
            agents_used=[],
            brain_routing={},
            workflow=[],
            execution_result={
                "ok": True,
                "output": "OMEGA planned the autonomous system without executing it.",
                "mode": "planned_only",
                "traces": [],
            },
            validation_result={
                "ok": True,
                "score": 1.0,
                "findings": ["Execution skipped by request; validate before live run."],
            },
            memory_saved={},
            next_actions=[
                "Review OMEGA plan.",
                "Run again with execute=true when ready for autonomous execution.",
            ],
        )

    def _infrastructure_optimization(
        self,
        request: OmegaRunRequest,
        selected_tools: list[str],
        execution: SaturnixExecutionResult,
    ) -> dict[str, Any]:
        if not request.optimize_infrastructure:
            return {
                "distributed": None,
                "self_healing": None,
                "note": "Infrastructure optimization disabled for this OMEGA run.",
            }
        distributed = self.distributed_engine.plan(
            DistributedIntelligenceRequest(
                mission=f"Optimize infrastructure for OMEGA goal: {request.goal}",
                workloads=[
                    "centralized orchestration and brain routing",
                    "workflow execution and verification",
                    "memory vault synchronization",
                    *selected_tools,
                ],
                privacy_level=_privacy_level_from_request(request),
                latency_priority=request.speed_priority,
                include_cloud_apis=not request.local_only,
            )
        )
        self_healing = self.self_healing_engine.diagnose(
            SelfHealingInfrastructureRequest(
                workflows={
                    "omega_execution": (
                        "healthy" if execution.execution_result.get("ok") else "failed"
                    )
                },
                active_brain=str(execution.brain_routing.get("selected_brain", "GPT")),
                fallback_brains=["Claude", "Gemini", "Gemma via Ollama"],
                auto_recover=False,
                notify_user=True,
            )
        )
        return {
            "distributed": distributed.model_dump(mode="json"),
            "self_healing": self_healing.model_dump(mode="json"),
        }

    def _persist_omega_memory(
        self,
        request: OmegaRunRequest,
        intent_summary: str,
        brain_route: dict[str, Any],
        agents: dict[str, Any],
        workflow: dict[str, Any],
        execution: dict[str, Any],
    ) -> dict[str, Any]:
        if not request.persist_memory:
            return {}
        payload = {
            "goal": request.goal,
            "intent_summary": intent_summary,
            "brain_route": brain_route,
            "agents": agents,
            "workflow": workflow,
            "execution": execution,
        }
        stored = self.neural_memory_engine.store(
            NeuralMemoryStoreRequest(
                content=json.dumps(payload, indent=2, default=str),
                category="reasoning_pattern",
                namespace="saturnix:omega",
                title=f"OMEGA run: {request.goal[:80]}",
                tags=["omega", "cognitive_os", "autonomous_execution"],
                metadata={
                    "goal": request.goal,
                    "execution_ok": execution.get("execution_result", {}).get("ok"),
                    "selected_brain": brain_route.get("selected_brain"),
                },
                importance_score=0.85,
                source="omega_engine",
                compress=True,
            )
        )
        return stored.model_dump(mode="json")


def _privacy_level(request: OmegaRunRequest, intent_local_only: bool) -> str:
    if request.local_only or intent_local_only:
        return "local"
    return request.privacy_level


def _privacy_level_from_request(request: OmegaRunRequest) -> str:
    return "local" if request.local_only else request.privacy_level


def _verification_from_execution(execution: SaturnixExecutionResult) -> dict[str, Any]:
    return execution.validation_result


def _evolution_plan(
    request: OmegaRunRequest,
    security_findings: list[str],
    validation_findings: list[Any],
    infrastructure: dict[str, Any],
) -> list[str]:
    plan = [
        "Store OMEGA run patterns in neural memory for future autonomous reuse.",
        "Promote successful agent structures into reusable blueprints.",
        "Feed validation findings into recursive prompt and workflow improvements.",
        "Continuously compare brain routing outcomes against verification scores.",
    ]
    if security_findings:
        plan.append("Prioritize secure orchestration fixes before expanding autonomy.")
    if validation_findings:
        plan.append("Convert validation findings into stronger acceptance checks.")
    if infrastructure.get("self_healing"):
        plan.append("Use self-healing diagnostics as uptime and resilience feedback.")
    if request.local_only:
        plan.append("Evolve local Ollama and edge execution paths for private workloads.")
    return plan


def _next_actions(
    execution: SaturnixExecutionResult,
    security_findings: list[str],
    memory: dict[str, Any],
) -> list[str]:
    actions = list(execution.next_actions)
    if security_findings:
        actions.append("Resolve Security Sentinel findings before increasing autonomy.")
    if memory:
        actions.append("Review stored OMEGA memory and reuse it for future goal planning.")
    actions.append("Run OMEGA again after improvements to close the recursive loop.")
    return _dedupe(actions)


def _dedupe(items: list[str]) -> list[str]:
    deduped: list[str] = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
    return deduped
