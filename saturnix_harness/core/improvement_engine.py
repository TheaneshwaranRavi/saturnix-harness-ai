from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime

from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.schemas import (
    MemoryType,
    RecursiveImprovementReport,
    SaturnixExecutionResult,
    SaveMemoryRequest,
    SearchMemoryRequest,
)

logger = logging.getLogger(__name__)


class RecursiveImprovementEngine:
    """SATURNIX Recursive Improvement Engine.

    The engine treats every execution as training signal. It analyzes failures,
    bottlenecks, hallucination risk, token waste, weak workflows, repeated
    mistakes, prompt quality, routing quality, coordination gaps, and memory
    quality. It then stores durable optimization strategies for future runs.
    """

    def __init__(self, memory: MemoryManager) -> None:
        self.memory = memory

    def analyze_execution(self, result: SaturnixExecutionResult) -> RecursiveImprovementReport:
        report = RecursiveImprovementReport()
        report.detected_failures = self._detect_failures(result)
        report.detected_bottlenecks = self._detect_bottlenecks(result)
        report.detected_hallucinations = self._detect_hallucinations(result)
        report.detected_wasted_tokens = self._detect_wasted_tokens(result)
        report.detected_weak_workflows = self._detect_weak_workflows(result)
        report.detected_repeated_mistakes = self._detect_repeated_mistakes(result)
        report.architecture_improvements = self._architecture_improvements(result, report)
        report.prompt_upgrades = self._prompt_upgrades(result, report)
        report.routing_improvements = self._routing_improvements(result, report)
        report.execution_improvements = self._execution_improvements(result, report)
        report.memory_improvements = self._memory_improvements(result, report)
        report.agent_coordination_improvements = self._coordination_improvements(result, report)
        report.optimization_report = self._optimization_summary(report)
        report.stored_strategy_ids = self._store_strategies(result, report)
        return report

    def _detect_failures(self, result: SaturnixExecutionResult) -> list[str]:
        failures: list[str] = []
        if not result.execution_result.get("ok", False):
            error = result.execution_result.get("error") or "one or more steps failed"
            failures.append(
                f"Execution failed: {error}"
            )
        if not result.validation_result.get("ok", False):
            failures.append("Validation failed or scored below acceptable threshold.")
        for trace in result.execution_result.get("traces", []):
            if trace.get("ok") is False:
                failures.append(
                    f"Step failed: {trace.get('step_name', trace.get('step_id', 'unknown'))}: "
                    f"{trace.get('error', 'no error detail')}"
                )
        return failures

    def _detect_bottlenecks(self, result: SaturnixExecutionResult) -> list[str]:
        bottlenecks: list[str] = []
        traces = result.execution_result.get("traces", [])
        slow_traces = [
            trace
            for trace in traces
            if _duration_seconds(trace.get("started_at"), trace.get("completed_at")) > 10
        ]
        for trace in slow_traces:
            bottlenecks.append(
                f"Slow workflow step: {trace.get('step_name', trace.get('step_id'))} "
                "took over 10 seconds."
            )
        if len(result.workflow) > 6:
            bottlenecks.append(
                "Workflow has many steps; consider grouping or parallelizing independent work."
            )
        if (
            result.brain_routing.get("selected_brain") == "Claude"
            and result.brain_routing.get("fallback_brain") == "GPT"
        ):
            bottlenecks.append(
                "Large-context routing may be expensive; summarize context before fallback handoff."
            )
        return bottlenecks

    def _detect_hallucinations(self, result: SaturnixExecutionResult) -> list[str]:
        output = str(result.execution_result.get("output", "")).lower()
        findings = [
            str(finding).lower()
            for finding in result.validation_result.get("findings", [])
        ]
        risks: list[str] = []
        if any("hallucination" in finding for finding in findings):
            risks.append("Verifier flagged hallucination risk.")
        absolute_claims = ("guaranteed", "100%", "always", "never fails")
        if any(token in output for token in absolute_claims):
            risks.append("Output contains absolute claims that should be evidence-checked.")
        if "according to" in output and "http" not in output:
            risks.append("Output references external authority without a source link.")
        return risks

    def _detect_wasted_tokens(self, result: SaturnixExecutionResult) -> list[str]:
        waste: list[str] = []
        output = str(result.execution_result.get("output", ""))
        if len(output) > 6000 and result.validation_result.get("score", 1.0) < 0.8:
            waste.append(
                "Large output still scored poorly; compress intermediate context and ask for "
                "targeted output."
            )
        prompts = [str(step.get("prompt", "")) for step in result.workflow]
        duplicate_prompt_count = len(prompts) - len(set(prompts))
        if duplicate_prompt_count > 0:
            waste.append(
                "Repeated workflow prompts detected; factor shared context into memory or a "
                "single preamble."
            )
        if len(result.execution_result.get("traces", [])) > 4 and len(output) < 300:
            waste.append(
                "Many execution steps produced a small output; reduce step count or merge "
                "low-value steps."
            )
        return waste

    def _detect_weak_workflows(self, result: SaturnixExecutionResult) -> list[str]:
        weak: list[str] = []
        step_names = [str(step.get("name", "")).lower() for step in result.workflow]
        if not any("verify" in name or "validate" in name for name in step_names):
            weak.append("Workflow lacks an explicit validation step.")
        if len(result.agents_used) <= 1 and (
            "research" in result.goal.lower() or "coding" in result.goal.lower()
        ):
            weak.append(
                "Complex goal used too few agents; add specialist plus verifier coordination."
            )
        if not result.workflow:
            weak.append("Workflow is empty; execution cannot be inspected or improved.")
        return weak

    def _detect_repeated_mistakes(self, result: SaturnixExecutionResult) -> list[str]:
        prior = self.memory.search_memory(
            SearchMemoryRequest(
                query=result.goal,
                namespace="saturnix:optimization",
                memory_type=MemoryType.project_history,
                limit=20,
                include_vector=False,
            )
        )
        kinds = Counter(record.kind for record in prior)
        mistakes: list[str] = []
        if kinds.get("optimization_strategy", 0) >= 2:
            mistakes.append(
                "Similar optimization strategies were already stored; recurring issue may need "
                "architecture change."
            )
        for finding in result.validation_result.get("findings", []):
            matches = [
                record
                for record in prior
                if str(finding).lower()[:80] in record.content.lower()
            ]
            if matches:
                mistakes.append(f"Repeated validation finding detected: {finding}")
        return mistakes

    def _architecture_improvements(
        self,
        result: SaturnixExecutionResult,
        report: RecursiveImprovementReport,
    ) -> list[str]:
        improvements = [
            "Keep improving modularity; never assume the current architecture is optimal."
        ]
        if report.detected_failures:
            improvements.append(
                "Add failure-specific recovery nodes to the workflow plan before final response."
            )
        if report.detected_weak_workflows:
            improvements.append(
                "Promote verification and memory-write steps into explicit workflow nodes."
            )
        if len(result.agents_used) < 2:
            improvements.append(
                "Use at least a producer agent and verifier agent for non-trivial goals."
            )
        return improvements

    def _prompt_upgrades(
        self,
        result: SaturnixExecutionResult,
        report: RecursiveImprovementReport,
    ) -> list[str]:
        upgrades = []
        if report.detected_hallucinations:
            upgrades.append(
                "Add evidence requirements: separate facts, assumptions, and unsupported claims."
            )
        if report.detected_wasted_tokens:
            upgrades.append(
                "Rewrite prompts to request concise intermediate outputs and final-only synthesis."
            )
        if not upgrades:
            upgrades.append(
                "Add an explicit acceptance checklist to agent prompts before execution."
            )
        return upgrades

    def _routing_improvements(
        self,
        result: SaturnixExecutionResult,
        report: RecursiveImprovementReport,
    ) -> list[str]:
        improvements = []
        selected = result.brain_routing.get("selected_brain")
        if report.detected_bottlenecks and selected in {"Claude", "GPT"}:
            improvements.append(
                "Pre-summarize large context locally before routing to cloud brains."
            )
        if report.detected_hallucinations:
            improvements.append(
                "Route fact-sensitive outputs through a verification brain before memory write."
            )
        if "private" in result.goal.lower() and "Ollama" not in str(selected):
            improvements.append("Prefer Ollama local brains for private or sensitive goals.")
        if not improvements:
            improvements.append(
                "Record route quality so future router scoring can learn from validation outcomes."
            )
        return improvements

    def _execution_improvements(
        self,
        result: SaturnixExecutionResult,
        report: RecursiveImprovementReport,
    ) -> list[str]:
        improvements = []
        if report.detected_failures:
            improvements.append(
                "Attach structured error objects to failed traces and retry only the failed step."
            )
        if report.detected_bottlenecks:
            improvements.append(
                "Track per-step duration and allow independent steps to run in parallel."
            )
        if report.detected_wasted_tokens:
            improvements.append("Cache repeated context in memory and reference it by memory id.")
        if not improvements:
            improvements.append(
                "Add execution quality metrics for step count, output size, validation score, "
                "and retries."
            )
        return improvements

    def _memory_improvements(
        self,
        result: SaturnixExecutionResult,
        report: RecursiveImprovementReport,
    ) -> list[str]:
        improvements = []
        if not result.memory_saved:
            improvements.append(
                "Ensure every execution writes a compact run summary and optimization strategy."
            )
        if report.detected_repeated_mistakes:
            improvements.append(
                "Promote repeated mistakes into durable prevention rules for future prompts."
            )
        improvements.append(
            "Store optimization strategies with tags for routing, prompts, execution, and "
            "verification."
        )
        return improvements

    def _coordination_improvements(
        self,
        result: SaturnixExecutionResult,
        report: RecursiveImprovementReport,
    ) -> list[str]:
        improvements = []
        if len(result.agents_used) > 1 and len(result.workflow) < len(result.agents_used):
            improvements.append(
                "Align workflow steps with agent responsibilities so every selected agent has "
                "a role."
            )
        if report.detected_weak_workflows:
            improvements.append(
                "Add handoff contracts between producer, specialist, and verifier agents."
            )
        if not improvements:
            improvements.append(
                "Add agent handoff summaries to reduce repeated context and improve coordination."
            )
        return improvements

    def _optimization_summary(self, report: RecursiveImprovementReport) -> list[str]:
        summary = [
            "Recursive improvement completed; current system is not assumed optimal.",
            f"Failures detected: {len(report.detected_failures)}.",
            f"Bottlenecks detected: {len(report.detected_bottlenecks)}.",
            f"Hallucination risks detected: {len(report.detected_hallucinations)}.",
            f"Token waste signals detected: {len(report.detected_wasted_tokens)}.",
            f"Weak workflow signals detected: {len(report.detected_weak_workflows)}.",
            f"Repeated mistake signals detected: {len(report.detected_repeated_mistakes)}.",
        ]
        return summary

    def _store_strategies(
        self,
        result: SaturnixExecutionResult,
        report: RecursiveImprovementReport,
    ) -> list[str]:
        strategies = {
            "architecture": report.architecture_improvements,
            "prompts": report.prompt_upgrades,
            "routing": report.routing_improvements,
            "execution": report.execution_improvements,
            "memory": report.memory_improvements,
            "coordination": report.agent_coordination_improvements,
        }
        record_ids: list[str] = []
        for category, items in strategies.items():
            if not items:
                continue
            record = self.memory.save_memory(
                SaveMemoryRequest(
                    content="\n".join(f"- {item}" for item in items),
                    memory_type=MemoryType.project_history,
                    namespace="saturnix:optimization",
                    kind="optimization_strategy",
                    title=f"{category.title()} optimization for: {result.goal[:80]}",
                    tags=["recursive_improvement", category],
                    metadata={
                        "goal": result.goal,
                        "validation_ok": result.validation_result.get("ok"),
                        "validation_score": result.validation_result.get("score"),
                    },
                    source="recursive_improvement_engine",
                )
            )
            record_ids.append(record.id)
        logger.info("Stored %s SATURNIX recursive optimization strategies.", len(record_ids))
        return record_ids


def _duration_seconds(started_at: str | None, completed_at: str | None) -> float:
    if not started_at or not completed_at:
        return 0.0
    try:
        start = _parse_datetime(started_at)
        end = _parse_datetime(completed_at)
    except ValueError:
        return 0.0
    return max(0.0, (end - start).total_seconds())


def _parse_datetime(value: str):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
