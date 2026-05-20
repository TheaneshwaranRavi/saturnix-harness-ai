from __future__ import annotations

from typing import Any

from saturnix_harness.agents_sdk.compat import load_agents_sdk
from saturnix_harness.agents_sdk.guardrails import SaturnixGuardrailEngine
from saturnix_harness.agents_sdk.registry import SaturnixAgentRegistry
from saturnix_harness.agents_sdk.tools import SaturnixSDKToolFactory
from saturnix_harness.brains.ollama_provider import SaturnixOllamaProvider
from saturnix_harness.config import Settings
from saturnix_harness.core.security_sentinel import SecuritySentinel
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.monitoring.events import MonitoringLayer
from saturnix_harness.schemas import (
    MemoryType,
    SaturnixAgentRegistryEntry,
    SaturnixAgentRunRequest,
    SaturnixAgentRunResult,
    SaturnixGuardrailDecision,
    SaturnixHandoffPlan,
    SaturnixHandoffRunResult,
    SaturnixHandoffStep,
    SaturnixStructuredAgentOutput,
    SaturnixTraceEvent,
    SaturnixTraceSummary,
    SaveMemoryRequest,
)


class SaturnixAgentManager:
    """OpenAI Agents SDK orchestration manager with local fallbacks."""

    def __init__(
        self,
        *,
        settings: Settings,
        memory: MemoryManager,
        monitoring: MonitoringLayer,
        ollama_provider: SaturnixOllamaProvider,
        security_sentinel: SecuritySentinel,
    ) -> None:
        self.settings = settings
        self.memory = memory
        self.monitoring = monitoring
        self.ollama_provider = ollama_provider
        self.security_sentinel = security_sentinel
        self.registry = SaturnixAgentRegistry()
        self.guardrails = SaturnixGuardrailEngine(security_sentinel)
        self.sdk = load_agents_sdk()
        self._trace_events: list[SaturnixTraceEvent] = []

    def sdk_status(self) -> dict[str, Any]:
        return {
            "enabled": self.settings.saturnix_enable_agents_sdk,
            "available": self.sdk.available,
            "import_error": self.sdk.error,
            "openai_configured": Settings.has_secret(self.settings.openai_api_key),
            "model": self.settings.openai_agents_model,
            "fallbacks": ["ollama", "gemma", "local coding model", "mock structured output"],
        }

    def registry_entries(self) -> list[SaturnixAgentRegistryEntry]:
        return self.registry.list()

    def handoff_plan(self) -> SaturnixHandoffPlan:
        order = [
            "Voice Agent",
            "Research Agent",
            "Coding Agent",
            "Verification Agent",
            "Memory Agent",
        ]
        return SaturnixHandoffPlan(
            workflow_name="voice-to-memory-verified-build",
            execution_order=order,
            steps=[
                SaturnixHandoffStep(
                    from_agent=order[index],
                    to_agent=order[index + 1],
                    reason=_handoff_reason(order[index], order[index + 1]),
                )
                for index in range(len(order) - 1)
            ],
        )

    async def run_agent(self, request: SaturnixAgentRunRequest) -> SaturnixAgentRunResult:
        entry = self.registry.require(request.agent_name)
        text = f"{request.goal}\n{request.context or ''}".strip()
        trace_events = [
            self._record_trace(
                "agent",
                entry.agent_name,
                "Agent execution requested.",
                {"session_id": request.session_id, "dry_run": request.dry_run},
            )
        ]
        guardrail = self.guardrails.evaluate(
            text=text,
            agent=entry,
            approved=request.approved,
            dry_run=request.dry_run,
        )
        trace_events.append(
            self._record_trace(
                "guardrail",
                entry.agent_name,
                "SATURNIX guardrails evaluated.",
                guardrail.model_dump(mode="json"),
            )
        )
        if not guardrail.allowed:
            return self._blocked_result(entry, guardrail, trace_events)
        if request.dry_run:
            output = _structured_fallback_output(entry, request, confidence=0.86)
            return self._result(
                entry=entry,
                runtime="dry_run",
                output=output,
                guardrail=guardrail,
                trace_events=trace_events,
            )
        if self._can_use_openai_agents():
            return await self._run_openai_agent(entry, request, guardrail, trace_events)
        return await self._run_local_fallback(entry, request, guardrail, trace_events)

    async def run_handoff_workflow(
        self,
        request: SaturnixAgentRunRequest,
    ) -> SaturnixHandoffRunResult:
        plan = self.handoff_plan()
        results: list[SaturnixAgentRunResult] = []
        context = request.context or ""
        for agent_name in plan.execution_order:
            self._record_trace(
                "handoff",
                agent_name,
                f"Running handoff step for {agent_name}.",
                {"workflow": plan.workflow_name},
            )
            step_result = await self.run_agent(
                SaturnixAgentRunRequest(
                    agent_name=agent_name,
                    goal=request.goal,
                    context=context,
                    session_id=request.session_id,
                    approved=request.approved,
                    dry_run=request.dry_run,
                    structured_output=request.structured_output,
                    max_turns=request.max_turns,
                )
            )
            results.append(step_result)
            if not step_result.ok:
                return SaturnixHandoffRunResult(ok=False, plan=plan, results=results)
            context = step_result.output.summary if step_result.output else step_result.raw_output
        return SaturnixHandoffRunResult(
            ok=True,
            plan=plan,
            results=results,
            final_output=results[-1].output if results else None,
        )

    def trace_summary(self, limit: int = 100) -> SaturnixTraceSummary:
        events = self._trace_events[-limit:]
        tool_usage = []
        security_events = []
        memory_logs = []
        token_usage = {"estimated_total": 0}
        for event in events:
            if event.event_type == "tool":
                tool_usage.append(event.metadata)
            if event.event_type in {"security", "guardrail"}:
                security_events.append(event.metadata)
            if event.event_type == "memory":
                memory_logs.append(event.metadata)
            token_usage["estimated_total"] += int(event.metadata.get("estimated_tokens", 0))
        return SaturnixTraceSummary(
            events=events,
            token_usage=token_usage,
            tool_usage=[],
            memory_access_logs=memory_logs,
            security_events=security_events,
        )

    def _can_use_openai_agents(self) -> bool:
        return (
            self.settings.saturnix_enable_agents_sdk
            and self.sdk.available
            and Settings.has_secret(self.settings.openai_api_key)
            and not self.settings.saturnix_local_only
        )

    async def _run_openai_agent(
        self,
        entry: SaturnixAgentRegistryEntry,
        request: SaturnixAgentRunRequest,
        guardrail: SaturnixGuardrailDecision,
        trace_events: list[SaturnixTraceEvent],
    ) -> SaturnixAgentRunResult:
        tool_factory = SaturnixSDKToolFactory(
            settings=self.settings,
            memory=self.memory,
            security_sentinel=self.security_sentinel,
        )
        sdk_guardrail = self.guardrails.sdk_input_guardrail(entry)
        input_guardrails = [sdk_guardrail] if sdk_guardrail else []
        handoffs = [
            self._build_sdk_agent(self.registry.require(agent_name), tool_factory, [])
            for agent_name in entry.handoffs
            if self.registry.get(agent_name)
        ]
        agent = self._build_sdk_agent(entry, tool_factory, handoffs, input_guardrails)
        try:
            with self.sdk.trace(
                workflow_name=f"SATURNIX {entry.agent_name}",
                group_id=request.session_id,
            ):
                session = self.sdk.SQLiteSession(request.session_id)
                result = await self.sdk.Runner.run(
                    agent,
                    request.goal if not request.context else f"{request.goal}\n\n{request.context}",
                    session=session,
                    max_turns=request.max_turns,
                )
        except Exception as exc:
            trace_events.append(
                self._record_trace(
                    "fallback",
                    entry.agent_name,
                    "OpenAI Agents SDK execution failed; local fallback engaged.",
                    {"error": f"{type(exc).__name__}: {exc}"},
                )
            )
            fallback = await self._run_local_fallback(entry, request, guardrail, trace_events)
            fallback.fallback_reason = f"OpenAI Agents SDK failed: {type(exc).__name__}: {exc}"
            return fallback
        output = _coerce_output(result.final_output, entry, request)
        usage = _extract_usage(result)
        return self._result(
            entry=entry,
            runtime="openai_agents_sdk",
            output=output,
            guardrail=guardrail,
            trace_events=trace_events,
            token_usage=usage,
            tool_usage=tool_factory.usage,
        )

    def _build_sdk_agent(
        self,
        entry: SaturnixAgentRegistryEntry,
        tool_factory: SaturnixSDKToolFactory,
        handoffs: list[Any],
        input_guardrails: list[Any] | None = None,
    ):
        return self.sdk.Agent(
            name=entry.agent_name,
            instructions=entry.instructions,
            model=self.settings.openai_agents_model,
            tools=tool_factory.build_for_agent(entry.tools),
            handoffs=handoffs,
            input_guardrails=input_guardrails or [],
            output_type=SaturnixStructuredAgentOutput,
        )

    async def _run_local_fallback(
        self,
        entry: SaturnixAgentRegistryEntry,
        request: SaturnixAgentRunRequest,
        guardrail: SaturnixGuardrailDecision,
        trace_events: list[SaturnixTraceEvent],
    ) -> SaturnixAgentRunResult:
        reason = self.sdk.error or "OpenAI Agents SDK unavailable or OpenAI API not configured."
        trace_events.append(
            self._record_trace(
                "fallback",
                entry.agent_name,
                "Using local SATURNIX fallback runtime.",
                {"reason": reason},
            )
        )
        prompt = f"{entry.instructions}\n\nGoal: {request.goal}\nContext: {request.context or ''}"
        fallback_text = _structured_fallback_output(entry, request, confidence=0.72).model_dump_json()
        if self.settings.saturnix_enable_ollama:
            generation = await self.ollama_provider.generate(
                prompt=prompt,
                model=self.settings.ollama_gemma_model,
                fallback_text=fallback_text,
            )
            raw = generation.output
            output = _coerce_output(raw, entry, request)
            runtime = f"ollama:{generation.model}"
            fallback_used = generation.fallback_used
            fallback_reason = generation.error or reason
        else:
            output = _structured_fallback_output(entry, request, confidence=0.72)
            raw = output.model_dump_json()
            runtime = "mock_structured_fallback"
            fallback_used = True
            fallback_reason = reason
        return self._result(
            entry=entry,
            runtime=runtime,
            output=output,
            raw_output=raw,
            guardrail=guardrail,
            trace_events=trace_events,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )

    def _blocked_result(
        self,
        entry: SaturnixAgentRegistryEntry,
        guardrail: SaturnixGuardrailDecision,
        trace_events: list[SaturnixTraceEvent],
    ) -> SaturnixAgentRunResult:
        return self._result(
            entry=entry,
            runtime="guardrail_blocked",
            output=None,
            raw_output="",
            guardrail=guardrail,
            trace_events=trace_events,
            security_events=[guardrail.model_dump(mode="json")],
        )

    def _result(
        self,
        *,
        entry: SaturnixAgentRegistryEntry,
        runtime: str,
        output: SaturnixStructuredAgentOutput | None,
        guardrail: SaturnixGuardrailDecision,
        trace_events: list[SaturnixTraceEvent],
        raw_output: str = "",
        token_usage: dict[str, Any] | None = None,
        tool_usage: list[Any] | None = None,
        memory_access_logs: list[dict[str, Any]] | None = None,
        security_events: list[dict[str, Any]] | None = None,
        fallback_used: bool = False,
        fallback_reason: str | None = None,
    ) -> SaturnixAgentRunResult:
        ok = guardrail.allowed and runtime != "guardrail_blocked"
        result = SaturnixAgentRunResult(
            ok=ok,
            agent_name=entry.agent_name,
            selected_runtime=runtime,
            output=output,
            raw_output=raw_output or (output.model_dump_json() if output else ""),
            guardrail=guardrail,
            trace_events=trace_events,
            token_usage=token_usage or _estimated_usage(output, raw_output),
            tool_usage=tool_usage or [],
            memory_access_logs=memory_access_logs or [],
            security_events=security_events or [guardrail.model_dump(mode="json")],
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        )
        self._persist_result(result)
        return result

    def _record_trace(
        self,
        event_type: str,
        agent_name: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> SaturnixTraceEvent:
        event = SaturnixTraceEvent(
            event_type=event_type,  # type: ignore[arg-type]
            agent_name=agent_name,
            message=message,
            metadata=metadata or {},
        )
        self._trace_events.append(event)
        self.monitoring.record(
            name=f"agents_sdk.{event_type}",
            message=message,
            metadata={"agent_name": agent_name, **(metadata or {})},
        )
        return event

    def _persist_result(self, result: SaturnixAgentRunResult) -> None:
        self.memory.save_memory(
            SaveMemoryRequest(
                content=result.model_dump_json(),
                memory_type=MemoryType.agent_execution_logs,
                namespace=self.settings.saturnix_agents_trace_namespace,
                kind="agents_sdk_run",
                title=f"Agents SDK run: {result.agent_name}",
                tags=["agents_sdk", result.agent_name, result.selected_runtime],
                metadata={
                    "agent_name": result.agent_name,
                    "runtime": result.selected_runtime,
                    "ok": result.ok,
                    "fallback_used": result.fallback_used,
                },
                source="agents_sdk",
            )
        )
        self._record_trace(
            "memory",
            result.agent_name,
            "Agent run trace persisted to SATURNIX memory.",
            {"namespace": self.settings.saturnix_agents_trace_namespace},
        )


def _handoff_reason(from_agent: str, to_agent: str) -> str:
    reasons = {
        ("Voice Agent", "Research Agent"): "Convert spoken intent into grounded context.",
        ("Research Agent", "Coding Agent"): "Turn researched context into implementation.",
        ("Coding Agent", "Verification Agent"): "Verify generated code and workflow claims.",
        ("Verification Agent", "Memory Agent"): "Store only verified reusable memory.",
    }
    return reasons.get((from_agent, to_agent), "SATURNIX delegated handoff.")


def _structured_fallback_output(
    entry: SaturnixAgentRegistryEntry,
    request: SaturnixAgentRunRequest,
    confidence: float,
) -> SaturnixStructuredAgentOutput:
    return SaturnixStructuredAgentOutput(
        summary=f"{entry.agent_name} prepared a SATURNIX structured response for: {request.goal}",
        reasoning=[
            "Applied SATURNIX operating doctrine.",
            "Checked guardrails before execution.",
            f"Selected best brain profile: {entry.best_brain}.",
        ],
        actions=[
            "Map intent",
            "Route brain",
            "Use least-privilege tools",
            "Verify output before execution",
        ],
        verification=[
            "Security guardrails evaluated.",
            "Risk level and permissions checked.",
            "Structured output returned.",
        ],
        memory_updates=[
            "Agent run trace can be saved under sdk:traces.",
        ],
        next_actions=[
            "Approve risky actions explicitly before non-dry-run execution.",
            "Use OpenAI API key to enable live Agents SDK execution.",
        ],
        confidence_score=confidence,
    )


def _coerce_output(
    value: Any,
    entry: SaturnixAgentRegistryEntry,
    request: SaturnixAgentRunRequest,
) -> SaturnixStructuredAgentOutput:
    if isinstance(value, SaturnixStructuredAgentOutput):
        return value
    if isinstance(value, dict):
        try:
            return SaturnixStructuredAgentOutput.model_validate(value)
        except Exception:
            pass
    if isinstance(value, str):
        try:
            return SaturnixStructuredAgentOutput.model_validate_json(value)
        except Exception:
            return SaturnixStructuredAgentOutput(
                summary=value[:1000],
                reasoning=["OpenAI Agents SDK returned text; SATURNIX wrapped it."],
                verification=["Output normalized into Pydantic structure."],
                next_actions=["Review normalized output before execution."],
                confidence_score=0.7,
            )
    return _structured_fallback_output(entry, request, confidence=0.6)


def _extract_usage(result: Any) -> dict[str, Any]:
    usage = getattr(result, "usage", None)
    if usage and hasattr(usage, "model_dump"):
        return usage.model_dump(mode="json")
    if usage:
        return {"raw": str(usage)}
    return {"estimated_total": 0}


def _estimated_usage(output: SaturnixStructuredAgentOutput | None, raw: str) -> dict[str, Any]:
    text = raw or (output.model_dump_json() if output else "")
    return {"estimated_total": max(1, len(text.split()))}
