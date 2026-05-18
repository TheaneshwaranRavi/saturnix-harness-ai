from __future__ import annotations

from dataclasses import dataclass

from saturnix_harness.schemas import (
    DistributedIntelligenceRequest,
    DistributedIntelligenceResult,
    DistributedNodeAssignment,
    DistributedResourceUsage,
)


class DistributedIntelligenceEngine:
    """Coordinate SATURNIX workloads across local, edge, vault, and cloud nodes."""

    def plan(self, request: DistributedIntelligenceRequest) -> DistributedIntelligenceResult:
        workloads = request.workloads or _default_workloads(request)
        assignments = [
            _assignment_for_node(node, workloads, request)
            for node in _active_nodes(request)
        ]
        resource_usage = [
            _resource_usage_for_node(node, request)
            for node in _active_nodes(request)
        ]
        return DistributedIntelligenceResult(
            node_assignments=assignments,
            resource_usage=resource_usage,
            optimization_plan=_optimization_plan(assignments, request),
            failover_strategy=_failover_strategy(request),
        )


@dataclass(frozen=True)
class _NodeProfile:
    name: str
    role: str
    keywords: set[str]
    cpu_profile: str
    memory_profile: str
    storage_profile: str
    network_profile: str
    constraints: list[str]
    monitoring_signals: list[str]


_NODES = [
    _NodeProfile(
        name="MacBook M1",
        role="Cognitive Core",
        keywords={
            "agent",
            "architecture",
            "brain",
            "coding",
            "coordination",
            "orchestration",
            "planning",
            "reasoning",
            "routing",
            "verification",
            "workflow",
        },
        cpu_profile="medium sustained CPU for orchestration, local models, and tests",
        memory_profile="high unified-memory pressure during local model and vector tasks",
        storage_profile="local project state, SQLite starter memory, and Chroma indexes",
        network_profile="selective outbound API access for cloud brains and GitHub",
        constraints=[
            "Protect battery and thermal headroom for long-running local inference.",
            "Keep secret-bearing orchestration on the cognitive core.",
        ],
        monitoring_signals=[
            "cpu_percent",
            "memory_pressure",
            "battery_state",
            "local_model_latency_ms",
            "orchestration_queue_depth",
        ],
    ),
    _NodeProfile(
        name="Raspberry Pi",
        role="Edge Automation Node",
        keywords={
            "automation",
            "camera",
            "device",
            "edge",
            "gpio",
            "iot",
            "offline",
            "raspberry",
            "sensor",
            "voice trigger",
        },
        cpu_profile="low-power CPU for triggers, sensors, and bounded scripts",
        memory_profile="low memory budget; avoid heavy LLM inference on edge",
        storage_profile="small local cache for offline queue and recent events",
        network_profile="intermittent LAN/Wi-Fi link to cognitive core",
        constraints=[
            "Run only signed or allowlisted edge automation tasks.",
            "Queue work locally when the cognitive core is unreachable.",
        ],
        monitoring_signals=[
            "heartbeat_age_seconds",
            "temperature_celsius",
            "disk_free_percent",
            "edge_queue_depth",
            "last_sync_at",
        ],
    ),
    _NodeProfile(
        name="External Storage",
        role="Memory Vault",
        keywords={
            "archive",
            "backup",
            "chroma",
            "memory",
            "snapshot",
            "storage",
            "sync",
            "vault",
            "vector",
        },
        cpu_profile="minimal CPU; checksum, compression, and indexing jobs only",
        memory_profile="low memory pressure; stream large backup operations",
        storage_profile="durable encrypted memory vault, backups, and artifacts",
        network_profile="local high-throughput sync path preferred over cloud upload",
        constraints=[
            "Encrypt sensitive snapshots before writing to external storage.",
            "Validate checksums before pruning local copies.",
        ],
        monitoring_signals=[
            "mount_status",
            "free_space_percent",
            "backup_age_minutes",
            "checksum_failures",
            "sync_lag_seconds",
        ],
    ),
    _NodeProfile(
        name="Cloud APIs",
        role="Intelligence Expansion",
        keywords={
            "api",
            "claude",
            "cloud",
            "deep analysis",
            "gemini",
            "groq",
            "large context",
            "openai",
            "speech",
            "web",
        },
        cpu_profile="remote elastic compute for high-context and specialized model calls",
        memory_profile="remote provider context windows; keep local summaries compact",
        storage_profile="no durable sensitive storage unless provider policy allows it",
        network_profile="WAN latency and provider availability dominate runtime",
        constraints=[
            "Do not send private workloads to cloud APIs unless policy allows it.",
            "Use local summaries and redaction before cloud expansion calls.",
        ],
        monitoring_signals=[
            "provider_latency_ms",
            "provider_error_rate",
            "token_usage",
            "rate_limit_remaining",
            "fallback_count",
        ],
    ),
]


def _active_nodes(request: DistributedIntelligenceRequest) -> list[_NodeProfile]:
    if request.include_cloud_apis:
        return list(_NODES)
    return [node for node in _NODES if node.name != "Cloud APIs"]


def _default_workloads(request: DistributedIntelligenceRequest) -> list[str]:
    workloads = [
        "centralized orchestration and brain routing",
        "workflow execution and verification",
        "edge automation and local sensor commands",
        "memory vault synchronization and backup",
        "node health monitoring and failover management",
    ]
    if request.include_cloud_apis:
        workloads.append("cloud intelligence expansion for large-context analysis")
    if request.latency_priority.lower() in {"high", "realtime", "low_latency"}:
        workloads.append("low-latency voice command routing")
    if request.privacy_level.lower() in {"private", "confidential", "restricted"}:
        workloads.append("private local execution and redacted cloud handoff")
    return workloads


def _assignment_for_node(
    node: _NodeProfile,
    workloads: list[str],
    request: DistributedIntelligenceRequest,
) -> DistributedNodeAssignment:
    assigned = [
        workload
        for workload in workloads
        if _matches_node(workload, node)
    ]
    if not assigned:
        assigned = _fallback_assignment(node, request)
    health = request.node_health.get(node.name, "unknown")
    if health.lower() in {"down", "offline", "degraded"}:
        assigned = [f"standby only until health recovers: {item}" for item in assigned]
    return DistributedNodeAssignment(
        node=node.name,
        role=node.role,
        assigned_workloads=assigned,
        reason=_assignment_reason(node, health, request),
        sync_policy=_sync_policy(node, request),
    )


def _matches_node(workload: str, node: _NodeProfile) -> bool:
    text = workload.lower()
    return any(keyword in text for keyword in node.keywords)


def _fallback_assignment(
    node: _NodeProfile,
    request: DistributedIntelligenceRequest,
) -> list[str]:
    if node.name == "MacBook M1":
        return ["primary orchestration, brain routing, and workflow supervision"]
    if node.name == "Raspberry Pi":
        return ["edge heartbeat, safe automation triggers, and offline queueing"]
    if node.name == "External Storage":
        return ["memory snapshots, backups, and synchronization checkpoints"]
    if request.privacy_level.lower() in {"private", "confidential", "restricted"}:
        return ["redacted cloud expansion only after cognitive-core approval"]
    return ["cloud model calls for large-context reasoning and voice expansion"]


def _assignment_reason(
    node: _NodeProfile,
    health: str,
    request: DistributedIntelligenceRequest,
) -> str:
    reason = f"{node.name} is the {node.role.lower()} for its workload class."
    if health != "unknown":
        reason += f" Reported health is {health}."
    if node.name == "Cloud APIs" and request.privacy_level.lower() != "standard":
        reason += " Privacy policy restricts cloud use to redacted or approved payloads."
    if node.name == "Raspberry Pi":
        reason += " It keeps physical automation close to devices and sensors."
    return reason


def _sync_policy(
    node: _NodeProfile,
    request: DistributedIntelligenceRequest,
) -> str:
    mode = request.synchronization_mode.lower()
    if node.name == "Raspberry Pi":
        return f"{mode} sync with local queue replay and signed command receipts"
    if node.name == "External Storage":
        return f"{mode} encrypted snapshots with checksum verification"
    if node.name == "Cloud APIs":
        return "stateless request/response handoff; persist only local summaries"
    return f"{mode} coordination state with memory writes after verified execution"


def _resource_usage_for_node(
    node: _NodeProfile,
    request: DistributedIntelligenceRequest,
) -> DistributedResourceUsage:
    constraints = list(node.constraints)
    if node.name == "Cloud APIs" and request.privacy_level.lower() != "standard":
        constraints.append("Cloud payloads must be redacted, summarized, or explicitly approved.")
    if node.name == "MacBook M1" and request.latency_priority.lower() in {
        "high",
        "realtime",
        "low_latency",
    }:
        constraints.append("Reserve local CPU for voice routing and interruption handling.")
    return DistributedResourceUsage(
        node=node.name,
        cpu_profile=node.cpu_profile,
        memory_profile=node.memory_profile,
        storage_profile=node.storage_profile,
        network_profile=node.network_profile,
        constraints=constraints,
        monitoring_signals=node.monitoring_signals,
    )


def _optimization_plan(
    assignments: list[DistributedNodeAssignment],
    request: DistributedIntelligenceRequest,
) -> list[str]:
    plan = [
        "Run orchestration, routing, verification, and secret-sensitive decisions on MacBook M1.",
        "Push bounded automation triggers to Raspberry Pi and keep heavy reasoning off the edge.",
        "Use External Storage as an encrypted memory vault with periodic verified snapshots.",
        "Record heartbeat, latency, queue depth, sync lag, and provider error metrics per node.",
    ]
    if request.include_cloud_apis:
        plan.append(
            "Use Cloud APIs only for large-context or specialized intelligence expansion, "
            "then persist compact local summaries."
        )
    if request.latency_priority.lower() in {"high", "realtime", "low_latency"}:
        plan.append(
            "Keep voice command classification local first, execute quick confirmations before "
            "long cloud calls, and allow interruption at every queue boundary."
        )
    if request.privacy_level.lower() in {"private", "confidential", "restricted"}:
        plan.append(
            "Route private tasks to MacBook M1 or Raspberry Pi; redact payloads before any cloud "
            "handoff."
        )
    degraded = [
        assignment.node
        for assignment in assignments
        if "standby only until health recovers" in " ".join(assignment.assigned_workloads)
    ]
    if degraded:
        plan.append(f"Reduce workload on degraded nodes: {', '.join(degraded)}.")
    return plan


def _failover_strategy(request: DistributedIntelligenceRequest) -> list[str]:
    strategy = [
        "If Raspberry Pi is offline, queue edge commands on MacBook M1 and replay only signed, "
        "idempotent actions when the node returns.",
        "If MacBook M1 is unavailable, pause orchestration and allow Raspberry Pi to run only "
        "pre-approved offline automation playbooks.",
        "If External Storage is unavailable, continue with local SQLite/Chroma memory and mark "
        "snapshots as pending until the vault remounts.",
    ]
    if request.include_cloud_apis:
        strategy.append(
            "If a cloud provider fails or rate-limits, fall back to another configured brain or "
            "local Ollama summarization."
        )
    else:
        strategy.append(
            "Cloud APIs are disabled; fail over to local Ollama and reduced-scope execution."
        )
    strategy.extend(
        [
            "Use heartbeat timeouts to mark nodes degraded before assigning new work.",
            "Require confirmation before failover executes destructive, external, or physical "
            "automation actions.",
            "Resolve split-brain state by treating MacBook M1 as source of truth and External "
            "Storage as the durable recovery point.",
        ]
    )
    return strategy
