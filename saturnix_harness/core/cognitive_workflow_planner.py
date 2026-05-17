from __future__ import annotations

import json
from dataclasses import dataclass

from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.core.agent_constructor import AgentConstructor
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.schemas import (
    BrainRouteRequest,
    CognitiveWorkflowPlanRequest,
    CognitiveWorkflowPlanResult,
    MemoryType,
    SaveMemoryRequest,
    WorkflowGraphEdge,
    WorkflowGraphNode,
    WorkflowTreeNode,
)


class CognitiveWorkflowPlanner:
    """Dependency-aware SATURNIX workflow planner.

    The planner converts complex goals into graph-shaped execution plans. It is
    deterministic for local/test use, but it still delegates agent and brain
    assignment to the existing SATURNIX constructor and router.
    """

    def __init__(
        self,
        brain_router: BrainRouter,
        agent_constructor: AgentConstructor,
        memory: MemoryManager,
    ) -> None:
        self.brain_router = brain_router
        self.agent_constructor = agent_constructor
        self.memory = memory

    def plan(self, request: CognitiveWorkflowPlanRequest) -> CognitiveWorkflowPlanResult:
        tasks = _build_task_specs(request)
        graph_nodes = [
            self._graph_node_from_spec(spec, request)
            for spec in tasks
        ]
        edges = _build_edges(graph_nodes)
        critical_path = _critical_path(graph_nodes)
        parallel_groups = _parallel_groups(graph_nodes, request.max_parallelism)
        runtime_seconds = _runtime_for_path(graph_nodes, critical_path)
        result = CognitiveWorkflowPlanResult(
            workflow_tree=_workflow_tree(graph_nodes),
            execution_graph={
                "nodes": [node.model_dump(mode="json") for node in graph_nodes],
                "edges": [edge.model_dump(mode="json") for edge in edges],
            },
            critical_path=critical_path,
            parallel_execution_opportunities=parallel_groups,
            estimated_execution_cost=_overall_cost(graph_nodes),
            estimated_runtime=_format_runtime(runtime_seconds),
            estimated_runtime_seconds=runtime_seconds,
        )
        if request.persist_plan:
            record = self.memory.save_memory(
                SaveMemoryRequest(
                    content=json.dumps(result.model_dump(mode="json"), indent=2),
                    memory_type=MemoryType.project_history,
                    namespace="saturnix:workflow_plans",
                    kind="cognitive_workflow_plan",
                    title=request.goal[:120],
                    tags=["workflow_plan", "cognitive_planner"],
                    metadata={
                        "goal": request.goal,
                        "node_count": len(graph_nodes),
                        "critical_path": critical_path,
                    },
                    source="cognitive_workflow_planner",
                )
            )
            result.memory_saved = {
                "namespace": record.namespace,
                "record_id": record.id,
                "kind": record.kind,
            }
        return result

    def _graph_node_from_spec(
        self,
        spec: "_TaskSpec",
        request: CognitiveWorkflowPlanRequest,
    ) -> WorkflowGraphNode:
        brain = self.brain_router.route_task(
            BrainRouteRequest(
                task=f"{request.goal}\n{spec.description}",
                task_type=spec.task_type,
                privacy_level=request.privacy_level,
                speed_priority=spec.speed_priority,
                context_size=spec.context_size,
                output_format=spec.output_format or request.output_format,
            )
        )
        return WorkflowGraphNode(
            id=spec.id,
            name=spec.name,
            description=spec.description,
            depends_on=spec.depends_on,
            priority=spec.priority,
            complexity=spec.complexity,
            assigned_agent=_agent_for_task(spec.task_type),
            assigned_brain=brain.selected_brain,
            estimated_cost=_cost_for_complexity(spec.complexity),
            estimated_runtime_seconds=_runtime_for_complexity(spec.complexity),
        )


@dataclass(frozen=True)
class _TaskSpec:
    id: str
    name: str
    description: str
    task_type: str
    depends_on: list[str]
    priority: int
    complexity: str
    speed_priority: str = "normal"
    context_size: str = "medium"
    output_format: str = ""


def _build_task_specs(request: CognitiveWorkflowPlanRequest) -> list[_TaskSpec]:
    text = _request_text(request)
    tasks = [
        _TaskSpec(
            id="intent",
            name="Map Human Intent",
            description="Clarify goal, constraints, acceptance criteria, and missing inputs.",
            task_type="planning",
            depends_on=[],
            priority=5,
            complexity="low",
        ),
        _TaskSpec(
            id="architecture",
            name="Design Agent Architecture",
            description="Choose agent roles, data flow, boundaries, and orchestration pattern.",
            task_type="architecture",
            depends_on=["intent"],
            priority=5,
            complexity="medium",
        ),
    ]

    specialist_ids: list[str] = []
    if _contains(text, {"research", "document", "contract", "source", "analysis"}):
        tasks.append(
            _TaskSpec(
                id="research",
                name="Research And Context Analysis",
                description="Gather, inspect, and synthesize relevant context and source material.",
                task_type="deep analysis",
                depends_on=["intent"],
                priority=4,
                complexity="medium",
                context_size="large" if "document" in text or "contract" in text else "medium",
            )
        )
        specialist_ids.append("research")
    if _contains(text, {"code", "coding", "api", "python", "fastapi", "test", "debug"}):
        deps = ["architecture"]
        if "research" in specialist_ids:
            deps.append("research")
        tasks.append(
            _TaskSpec(
                id="implementation",
                name="Implement Technical Work",
                description=(
                    "Produce code, configuration, interfaces, or concrete technical output."
                ),
                task_type="coding",
                depends_on=deps,
                priority=5,
                complexity="high",
                speed_priority=request.speed_priority,
                output_format="code",
            )
        )
        specialist_ids.append("implementation")
    if _contains(text, {"automation", "workflow", "webhook", "tool", "function", "n8n"}):
        tasks.append(
            _TaskSpec(
                id="automation",
                name="Model Automation Workflow",
                description="Define triggers, tool calls, permissions, rollback, and outputs.",
                task_type="automation",
                depends_on=["architecture"],
                priority=4,
                complexity="medium",
                output_format="json schema",
            )
        )
        specialist_ids.append("automation")
    if _contains(text, {"security", "private", "secret", "auth", "permission", "risk"}):
        tasks.append(
            _TaskSpec(
                id="security",
                name="Assess Security And Privacy",
                description="Detect secret exposure, risky tool actions, and approval boundaries.",
                task_type="security",
                depends_on=["architecture"],
                priority=5,
                complexity="medium",
            )
        )
        specialist_ids.append("security")
    if _contains(text, {"json", "schema", "structured", "function calling"}):
        tasks.append(
            _TaskSpec(
                id="schema",
                name="Validate Structured Output Contract",
                description="Design and validate schemas, function contracts, and output shape.",
                task_type="structured JSON",
                depends_on=["architecture"],
                priority=4,
                complexity="medium",
                output_format="json schema",
            )
        )
        specialist_ids.append("schema")
    if _contains(text, {"voice", "speech", "audio", "transcribe", "tts", "stt"}):
        tasks.append(
            _TaskSpec(
                id="voice",
                name="Plan Voice Interaction Layer",
                description=(
                    "Map audio intake, transcription, command extraction, and spoken reply."
                ),
                task_type="voice",
                depends_on=["intent"],
                priority=3,
                complexity="medium",
            )
        )
        specialist_ids.append("voice")
    if _contains(text, {"memory", "recall", "remember", "history", "vector"}):
        tasks.append(
            _TaskSpec(
                id="memory",
                name="Plan Memory Strategy",
                description="Define recall, write, deduplication, retention, and namespace rules.",
                task_type="memory",
                depends_on=["architecture"],
                priority=4,
                complexity="medium",
            )
        )
        specialist_ids.append("memory")

    synthesis_deps = specialist_ids or ["architecture"]
    tasks.append(
        _TaskSpec(
            id="synthesis",
            name="Synthesize Final Plan",
            description="Merge specialist outputs into one coherent execution-ready plan.",
            task_type="planning",
            depends_on=synthesis_deps,
            priority=4,
            complexity="medium" if len(synthesis_deps) < 4 else "high",
        )
    )
    tasks.append(
            _TaskSpec(
                id="verification",
                name="Verify Workflow Plan",
                description=(
                    "Check missing requirements, weak dependencies, hallucination risk, and safety."
                ),
            task_type="verification",
            depends_on=["synthesis"],
            priority=5,
            complexity="medium",
        )
    )
    tasks.append(
        _TaskSpec(
            id="memory_write",
            name="Store Workflow Intelligence",
            description="Save reusable workflow strategy, failure risks, and optimization notes.",
            task_type="memory",
            depends_on=["verification"],
            priority=2,
            complexity="low",
        )
    )
    return tasks


def _workflow_tree(nodes: list[WorkflowGraphNode]) -> WorkflowTreeNode:
    by_id = {node.id: node for node in nodes}
    children_by_parent: dict[str, list[str]] = {node.id: [] for node in nodes}
    root_ids: list[str] = []
    for node in nodes:
        if not node.depends_on:
            root_ids.append(node.id)
        for parent in node.depends_on:
            children_by_parent.setdefault(parent, []).append(node.id)

    def build(node_id: str) -> WorkflowTreeNode:
        node = by_id[node_id]
        return WorkflowTreeNode(
            id=node.id,
            name=node.name,
            purpose=node.description,
            agent=node.assigned_agent,
            brain=node.assigned_brain,
            complexity=node.complexity,
            children=[build(child_id) for child_id in children_by_parent.get(node_id, [])],
        )

    if len(root_ids) == 1:
        return build(root_ids[0])
    return WorkflowTreeNode(
        id="root",
        name="SATURNIX Cognitive Workflow",
        purpose="Root container for independent workflow roots.",
        agent="Core Orchestrator",
        brain="GPT",
        complexity="medium",
        children=[build(root_id) for root_id in root_ids],
    )


def _build_edges(nodes: list[WorkflowGraphNode]) -> list[WorkflowGraphEdge]:
    node_names = {node.id: node.name for node in nodes}
    edges: list[WorkflowGraphEdge] = []
    for node in nodes:
        for dependency in node.depends_on:
            edges.append(
                WorkflowGraphEdge(
                    source=dependency,
                    target=node.id,
                    reason=f"{node.name} depends on {node_names.get(dependency, dependency)}.",
                )
            )
    return edges


def _critical_path(nodes: list[WorkflowGraphNode]) -> list[str]:
    by_id = {node.id: node for node in nodes}
    memo: dict[str, tuple[int, list[str]]] = {}

    def best_path(node_id: str) -> tuple[int, list[str]]:
        if node_id in memo:
            return memo[node_id]
        node = by_id[node_id]
        weight = _complexity_points(node.complexity)
        if not node.depends_on:
            memo[node_id] = (weight, [node_id])
            return memo[node_id]
        parent_score, parent_path = max(
            (best_path(parent) for parent in node.depends_on if parent in by_id),
            key=lambda item: item[0],
            default=(0, []),
        )
        memo[node_id] = (parent_score + weight, [*parent_path, node_id])
        return memo[node_id]

    _, path = max((best_path(node.id) for node in nodes), key=lambda item: item[0])
    return path


def _parallel_groups(
    nodes: list[WorkflowGraphNode],
    max_parallelism: int,
) -> list[list[str]]:
    remaining = {node.id: set(node.depends_on) for node in nodes}
    completed: set[str] = set()
    groups: list[list[str]] = []
    while remaining:
        ready = sorted(
            node_id
            for node_id, dependencies in remaining.items()
            if dependencies.issubset(completed)
        )
        if not ready:
            break
        group = ready[:max_parallelism]
        if len(group) > 1:
            groups.append(group)
        completed.update(group)
        for node_id in group:
            remaining.pop(node_id, None)
    return groups


def _runtime_for_path(nodes: list[WorkflowGraphNode], path: list[str]) -> int:
    by_id = {node.id: node for node in nodes}
    return sum(by_id[node_id].estimated_runtime_seconds for node_id in path if node_id in by_id)


def _overall_cost(nodes: list[WorkflowGraphNode]) -> str:
    score = sum(_complexity_points(node.complexity) for node in nodes)
    if score <= 8:
        return "low"
    if score <= 15:
        return "medium"
    if score <= 23:
        return "high"
    return "very_high"


def _format_runtime(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} seconds"
    minutes, remainder = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} minutes {remainder} seconds"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} hours {minutes} minutes"


def _agent_for_task(task_type: str) -> str:
    normalized = task_type.lower()
    if any(token in normalized for token in ("coding", "code")):
        return "Coding Agent"
    if any(token in normalized for token in ("analysis", "research", "document")):
        return "Research Agent"
    if any(token in normalized for token in ("automation", "function", "tool")):
        return "Automation Agent"
    if "voice" in normalized:
        return "Voice Agent"
    if "memory" in normalized:
        return "Memory Agent"
    if any(token in normalized for token in ("verification", "security")):
        return "Verification Agent"
    return "Research Agent"


def _cost_for_complexity(complexity: str) -> str:
    return {
        "low": "low",
        "medium": "medium",
        "high": "high",
    }.get(complexity, "medium")


def _runtime_for_complexity(complexity: str) -> int:
    return {
        "low": 120,
        "medium": 360,
        "high": 720,
    }.get(complexity, 360)


def _complexity_points(complexity: str) -> int:
    return {
        "low": 1,
        "medium": 3,
        "high": 5,
    }.get(complexity, 3)


def _request_text(request: CognitiveWorkflowPlanRequest) -> str:
    return " ".join(
        [
            request.goal,
            request.context or "",
            request.task_type,
            request.privacy_level,
            request.output_format,
            " ".join(request.constraints),
            " ".join(request.required_tools),
        ]
    ).lower()


def _contains(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)
