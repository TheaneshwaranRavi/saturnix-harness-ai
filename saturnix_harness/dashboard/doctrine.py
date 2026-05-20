from __future__ import annotations

from typing import Any

from saturnix_harness.schemas import (
    DashboardAgentDefinition,
    DashboardSecurityScanResult,
    DataGuardianClassifyResult,
    PermissionLevel,
)


class SaturnixOperatingDoctrine:
    """Codifies SATURNIX-HARNESS as infrastructure, not chatbot behavior."""

    identity = "personalized_ai_infrastructure_system"
    anti_identity = "chatbot"

    def summary(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "anti_identity": self.anti_identity,
            "behavior_modes": [
                "AI operating dashboard",
                "secure agent manager",
                "personal memory vault",
                "cyber-defense layer",
                "workflow automation engine",
                "local/cloud brain router",
                "self-improving engineering harness",
            ],
            "core_principles": _principles(),
            "mandatory_gates": [
                "security_scan_before_execution",
                "data_classification_before_memory_write",
                "minimum_permissions_for_agents",
                "human_approval_for_risky_actions",
                "audit_log_for_sensitive_actions",
                "verification_before_execution",
            ],
        }

    def preflight_agent_execution(
        self,
        *,
        agent: DashboardAgentDefinition,
        security: DashboardSecurityScanResult,
        classification: DataGuardianClassifyResult,
        dry_run: bool,
        approved: bool,
    ) -> dict[str, Any]:
        required_approvals: list[str] = []
        blocked_actions: list[str] = []

        if security.lockdown_required:
            blocked_actions.append("Security Sentinel requires lockdown before execution.")
        blocked_actions.extend(security.blocked_actions)
        blocked_actions.extend(classification.blocked_actions)

        if not dry_run and _has_risky_permission(agent.permissions):
            required_approvals.append(
                "Agent has tool, file, network, memory-write, or admin permissions."
            )
        if not dry_run and agent.risk_level in {"HIGH", "CRITICAL"}:
            required_approvals.append(f"Agent risk level is {agent.risk_level}.")
        if not dry_run:
            required_approvals.append("Verification-before-execution gate requires approval.")

        approval_required = bool(required_approvals)
        allowed = not blocked_actions and (dry_run or approved or not approval_required)
        return {
            "identity": self.identity,
            "allowed": allowed,
            "dry_run": dry_run,
            "approval_required": approval_required and not approved and not dry_run,
            "required_approvals": required_approvals,
            "blocked_actions": blocked_actions,
            "principles_enforced": [
                "security_first",
                "privacy_first",
                "verification_before_execution",
                "minimum_required_permissions",
                "human_approval_for_risky_actions",
                "full_audit_trail",
            ],
        }


def _has_risky_permission(permissions: list[PermissionLevel]) -> bool:
    risky = {
        PermissionLevel.memory_write,
        PermissionLevel.tool_execution,
        PermissionLevel.file_access,
        PermissionLevel.network_access,
        PermissionLevel.admin_security,
    }
    return any(permission in risky for permission in permissions)


def _principles() -> list[dict[str, str]]:
    return [
        {
            "id": "security_first",
            "label": "Security first",
            "enforcement": "Scan prompts, workflows, commands, paths, and secrets before execution.",
        },
        {
            "id": "privacy_first",
            "label": "Privacy first",
            "enforcement": "Classify data sensitivity and encrypt personal memory and API secrets.",
        },
        {
            "id": "personalization_first",
            "label": "Personalization first",
            "enforcement": "Bind dashboard defaults to the owner profile and hardware topology.",
        },
        {
            "id": "verification_before_execution",
            "label": "Verification before execution",
            "enforcement": "Run preflight checks and require approval before non-dry-run actions.",
        },
        {
            "id": "minimum_required_permissions",
            "label": "Minimum required permissions",
            "enforcement": "Every agent starts with READ_ONLY and receives only explicit capabilities.",
        },
        {
            "id": "local_first_memory",
            "label": "Local-first memory",
            "enforcement": "Use SQLite and local vector memory paths before external persistence.",
        },
        {
            "id": "multi_brain_intelligence",
            "label": "Multi-brain intelligence",
            "enforcement": "Route GPT, Claude, Gemini, Ollama, and Groq by task characteristics.",
        },
        {
            "id": "human_approval_for_risky_actions",
            "label": "Human approval for risky actions",
            "enforcement": "Block risky non-dry-run execution until explicit approval is provided.",
        },
        {
            "id": "full_audit_trail",
            "label": "Full audit trail",
            "enforcement": "Record sensitive dashboard, memory, security, agent, and workflow actions.",
        },
        {
            "id": "continuous_improvement",
            "label": "Continuous improvement",
            "enforcement": "Keep optimization and verification outputs available for recursive upgrades.",
        },
    ]
