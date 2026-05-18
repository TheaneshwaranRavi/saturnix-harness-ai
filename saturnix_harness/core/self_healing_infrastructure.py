from __future__ import annotations

from saturnix_harness.schemas import (
    SelfHealingAction,
    SelfHealingIncident,
    SelfHealingInfrastructureRequest,
    SelfHealingInfrastructureResult,
)


class SelfHealingInfrastructureEngine:
    """Detect infrastructure failures and produce recovery plans for SATURNIX."""

    def diagnose(
        self,
        request: SelfHealingInfrastructureRequest,
    ) -> SelfHealingInfrastructureResult:
        incidents = _detect_incidents(request)
        recovery_actions = _recovery_actions(request, incidents)
        fallback_brain = _select_fallback_brain(request, incidents)
        return SelfHealingInfrastructureResult(
            overall_status=_overall_status(incidents, request.auto_recover),
            health_score=_health_score(incidents),
            incidents_detected=incidents,
            recovery_actions=recovery_actions,
            fallback_brain=fallback_brain,
            isolation_plan=_isolation_plan(incidents),
            workflow_rebuilds=_workflow_rebuilds(request, incidents),
            notifications=_notifications(request, incidents, fallback_brain),
            resilience_plan=_resilience_plan(request, incidents),
        )


def _detect_incidents(
    request: SelfHealingInfrastructureRequest,
) -> list[SelfHealingIncident]:
    incidents: list[SelfHealingIncident] = []
    incidents.extend(_detect_container_failures(request.containers))
    incidents.extend(_detect_api_failures(request.apis))
    incidents.extend(_detect_memory_overload(request.memory_usage_percent))
    incidents.extend(_detect_disk_failures(request.disk_usage_percent))
    incidents.extend(_detect_network_failures(request.network_status))
    incidents.extend(_detect_workflow_failures(request.workflows))
    incidents.extend(_detect_hanging_processes(request.processes))
    return incidents


def _detect_container_failures(containers: dict[str, str]) -> list[SelfHealingIncident]:
    incidents: list[SelfHealingIncident] = []
    for name, status in containers.items():
        normalized = status.lower()
        if any(marker in normalized for marker in {"crashed", "exited", "dead", "oom"}):
            severity = "critical" if "oom" in normalized else "high"
            incidents.append(
                SelfHealingIncident(
                    component=name,
                    failure_type="crashed_container",
                    severity=severity,
                    evidence=f"container status={status}",
                    impact="Containerized SATURNIX service may be unavailable.",
                )
            )
        elif any(marker in normalized for marker in {"restarting", "unhealthy"}):
            incidents.append(
                SelfHealingIncident(
                    component=name,
                    failure_type="unstable_container",
                    severity="medium",
                    evidence=f"container status={status}",
                    impact="Service may be flapping and needs health-gated restart.",
                )
            )
    return incidents


def _detect_api_failures(apis: dict[str, str]) -> list[SelfHealingIncident]:
    incidents: list[SelfHealingIncident] = []
    for name, status in apis.items():
        normalized = status.lower()
        if any(marker in normalized for marker in {"down", "timeout", "unreachable"}):
            incidents.append(
                SelfHealingIncident(
                    component=name,
                    failure_type="failed_api",
                    severity="high",
                    evidence=f"api status={status}",
                    impact="Brain, tool, or integration requests may fail.",
                )
            )
        elif _looks_like_5xx(normalized):
            incidents.append(
                SelfHealingIncident(
                    component=name,
                    failure_type="failed_api",
                    severity="medium",
                    evidence=f"api status={status}",
                    impact="Provider is returning server errors and should use fallback routing.",
                )
            )
    return incidents


def _detect_memory_overload(
    usage_percent: float | None,
) -> list[SelfHealingIncident]:
    if usage_percent is None or usage_percent < 85:
        return []
    severity = "critical" if usage_percent >= 95 else "high"
    return [
        SelfHealingIncident(
            component="system_memory",
            failure_type="memory_overload",
            severity=severity,
            evidence=f"memory_usage_percent={usage_percent}",
            impact="Inference, Chroma, workflow execution, and API latency may degrade.",
        )
    ]


def _detect_disk_failures(usage_percent: float | None) -> list[SelfHealingIncident]:
    if usage_percent is None or usage_percent < 90:
        return []
    severity = "critical" if usage_percent >= 97 else "high"
    return [
        SelfHealingIncident(
            component="disk_storage",
            failure_type="disk_failure",
            severity=severity,
            evidence=f"disk_usage_percent={usage_percent}",
            impact="Memory persistence, logs, vector indexes, and backups may fail.",
        )
    ]


def _detect_network_failures(status: str) -> list[SelfHealingIncident]:
    normalized = status.lower()
    if normalized in {"healthy", "ok", "online", "nominal"}:
        return []
    severity = "critical" if normalized in {"down", "offline"} else "medium"
    return [
        SelfHealingIncident(
            component="network",
            failure_type="network_failure",
            severity=severity,
            evidence=f"network_status={status}",
            impact="Cloud APIs, distributed nodes, GitHub, and remote memory sync may fail.",
        )
    ]


def _detect_workflow_failures(workflows: dict[str, str]) -> list[SelfHealingIncident]:
    incidents: list[SelfHealingIncident] = []
    for name, status in workflows.items():
        normalized = status.lower()
        if any(marker in normalized for marker in {"corrupt", "invalid", "failed"}):
            incidents.append(
                SelfHealingIncident(
                    component=name,
                    failure_type="corrupted_workflow",
                    severity="high",
                    evidence=f"workflow status={status}",
                    impact="Workflow output cannot be trusted until rebuilt and reverified.",
                )
            )
    return incidents


def _detect_hanging_processes(processes: dict[str, str]) -> list[SelfHealingIncident]:
    incidents: list[SelfHealingIncident] = []
    for name, status in processes.items():
        normalized = status.lower()
        if any(marker in normalized for marker in {"hang", "stuck", "blocked", "zombie"}):
            incidents.append(
                SelfHealingIncident(
                    component=name,
                    failure_type="hanging_process",
                    severity="medium",
                    evidence=f"process status={status}",
                    impact="Worker capacity may be exhausted by a blocked process.",
                )
            )
    return incidents


def _recovery_actions(
    request: SelfHealingInfrastructureRequest,
    incidents: list[SelfHealingIncident],
) -> list[SelfHealingAction]:
    actions: list[SelfHealingAction] = []
    for incident in incidents:
        if incident.failure_type in {"crashed_container", "unstable_container"}:
            actions.append(
                _action(
                    action="restart_service",
                    target=incident.component,
                    reason="Restart container with health-check gate and backoff.",
                    safe=True,
                )
            )
        elif incident.failure_type == "failed_api":
            actions.append(
                _action(
                    action="switch_fallback_brain",
                    target=incident.component,
                    reason="Provider/API failure detected; route traffic to fallback brain.",
                    safe=True,
                )
            )
        elif incident.failure_type == "memory_overload":
            actions.extend(
                [
                    _action(
                        action="shed_noncritical_workloads",
                        target="execution_queue",
                        reason="Free memory by pausing low-priority jobs.",
                        safe=True,
                    ),
                    _action(
                        action="recover_memory",
                        target="memory_manager",
                        reason="Compact caches and move old context into persisted memory.",
                        safe=True,
                    ),
                ]
            )
        elif incident.failure_type == "disk_failure":
            actions.append(
                _action(
                    action="recover_memory",
                    target="memory_vault",
                    reason="Rotate logs, validate snapshots, and free space before writes.",
                    safe=False,
                )
            )
        elif incident.failure_type == "network_failure":
            actions.append(
                _action(
                    action="isolate_faulty_module",
                    target="remote_connectors",
                    reason="Disable remote calls and queue sync until network recovers.",
                    safe=True,
                )
            )
        elif incident.failure_type == "corrupted_workflow":
            actions.append(
                _action(
                    action="rebuild_failed_workflow",
                    target=incident.component,
                    reason="Regenerate workflow from last valid intent and rerun verification.",
                    safe=True,
                )
            )
        elif incident.failure_type == "hanging_process":
            actions.append(
                _action(
                    action="isolate_faulty_module",
                    target=incident.component,
                    reason="Quarantine hanging process and start replacement worker.",
                    safe=True,
                )
            )
    if request.notify_user and incidents:
        actions.append(
            _action(
                action="notify_user",
                target="operator",
                reason="Report detected failures, recovery plan, and actions requiring approval.",
                safe=True,
            )
        )
    return actions


def _action(
    action: str,
    target: str,
    reason: str,
    safe: bool,
) -> SelfHealingAction:
    return SelfHealingAction(
        action=action,
        target=target,
        reason=reason,
        safe_to_auto_execute=safe,
        confirmation_required=not safe,
    )


def _select_fallback_brain(
    request: SelfHealingInfrastructureRequest,
    incidents: list[SelfHealingIncident],
) -> str | None:
    failed_components = " ".join(incident.component.lower() for incident in incidents)
    for brain in request.fallback_brains:
        if brain.lower() != request.active_brain.lower() and brain.lower() not in failed_components:
            return brain
    return request.fallback_brains[0] if request.fallback_brains else None


def _isolation_plan(incidents: list[SelfHealingIncident]) -> list[str]:
    plan = []
    for incident in incidents:
        if incident.severity in {"high", "critical"}:
            plan.append(
                f"Isolate {incident.component} from new work until {incident.failure_type} "
                "is recovered and health checks pass."
            )
    if not plan:
        plan.append("No isolation needed; continue monitoring normal health signals.")
    return plan


def _workflow_rebuilds(
    request: SelfHealingInfrastructureRequest,
    incidents: list[SelfHealingIncident],
) -> list[str]:
    rebuilds = [
        (
            f"Rebuild workflow {incident.component} from saved intent, dependency graph, "
            "and verification rules."
        )
        for incident in incidents
        if incident.failure_type == "corrupted_workflow"
    ]
    if any(incident.failure_type == "network_failure" for incident in incidents):
        rebuilds.append("Rebuild remote-dependent workflows as offline/local fallback variants.")
    if any(incident.failure_type == "failed_api" for incident in incidents):
        rebuilds.append(
            f"Rebuild brain route using fallback brain {request.fallback_brains[:1] or ['local']}"
        )
    return rebuilds or ["No workflow rebuild required for current health state."]


def _notifications(
    request: SelfHealingInfrastructureRequest,
    incidents: list[SelfHealingIncident],
    fallback_brain: str | None,
) -> list[str]:
    if not request.notify_user:
        return []
    if not incidents:
        return ["SATURNIX infrastructure is healthy; no recovery actions required."]
    critical = [incident.component for incident in incidents if incident.severity == "critical"]
    notifications = [
        f"Detected {len(incidents)} infrastructure incident(s); recovery plan is ready.",
    ]
    if critical:
        notifications.append(f"Critical components require attention: {', '.join(critical)}.")
    if fallback_brain:
        notifications.append(f"Fallback brain candidate selected: {fallback_brain}.")
    return notifications


def _resilience_plan(
    request: SelfHealingInfrastructureRequest,
    incidents: list[SelfHealingIncident],
) -> list[str]:
    plan = [
        "Run health probes on containers, APIs, memory, disk, network, workflows, and workers.",
        "Apply safe recovery actions automatically; require confirmation for destructive cleanup.",
        "Keep brain routing fallback chains warm for failed API or model providers.",
        "Persist recovery incidents so recurring failures become optimization signals.",
    ]
    if any(incident.failure_type == "disk_failure" for incident in incidents):
        plan.append("Increase memory vault free-space alerts and enforce log retention limits.")
    if any(incident.failure_type == "memory_overload" for incident in incidents):
        plan.append("Reduce concurrent local inference and compact vector-memory context windows.")
    if any(incident.failure_type == "hanging_process" for incident in incidents):
        plan.append("Add worker timeouts, heartbeats, and replacement-worker launch policy.")
    if request.auto_recover:
        plan.append("Auto-recovery is enabled; execute only actions marked safe_to_auto_execute.")
    else:
        plan.append("Auto-recovery is disabled; return recovery plan for operator approval.")
    return plan


def _overall_status(
    incidents: list[SelfHealingIncident],
    auto_recover: bool,
) -> str:
    if not incidents:
        return "healthy"
    if auto_recover and not any(
        incident.severity == "critical" for incident in incidents
    ):
        return "recovering"
    if any(incident.severity == "critical" for incident in incidents):
        return "critical"
    return "degraded"


def _health_score(incidents: list[SelfHealingIncident]) -> int:
    score = 100
    penalties = {"low": 5, "medium": 12, "high": 22, "critical": 35}
    for incident in incidents:
        score -= penalties[incident.severity]
    return max(0, score)


def _looks_like_5xx(status: str) -> bool:
    return any(token in status for token in {"500", "502", "503", "504", "5xx"})
