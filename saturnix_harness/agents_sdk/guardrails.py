from __future__ import annotations

from typing import Any

from saturnix_harness.agents_sdk.compat import load_agents_sdk
from saturnix_harness.core.security_sentinel import SecuritySentinel
from saturnix_harness.schemas import (
    PermissionLevel,
    SaturnixAgentRegistryEntry,
    SaturnixGuardrailDecision,
    SecurityScanRequest,
)


class SaturnixGuardrailEngine:
    """Central guardrail enforcement for SDK and fallback agent execution."""

    def __init__(self, security_sentinel: SecuritySentinel | None = None) -> None:
        self.security_sentinel = security_sentinel or SecuritySentinel()

    def evaluate(
        self,
        *,
        text: str,
        agent: SaturnixAgentRegistryEntry,
        approved: bool = False,
        dry_run: bool = False,
        file_paths: list[str] | None = None,
        actions: list[str] | None = None,
    ) -> SaturnixGuardrailDecision:
        scan = self.security_sentinel.scan(
            SecurityScanRequest(
                prompt=text,
                task=agent.purpose,
                file_paths=file_paths or [],
                actions=actions or [],
                sensitivity_level=_sensitivity(agent),
            )
        )
        blocked_actions = list(scan.blocked_actions)
        approval_required = (
            not dry_run
            and not approved
            and (agent.risk_level in {"HIGH", "CRITICAL"} or _has_risky_permission(agent))
        )
        detected = list(scan.risks_detected)
        if approval_required:
            detected.append("Human approval required for risky non-dry-run action.")
        return SaturnixGuardrailDecision(
            allowed=not blocked_actions and not approval_required,
            approval_required=approval_required,
            risk_level=agent.risk_level,
            detected_risks=detected,
            blocked_actions=blocked_actions,
            recommended_fixes=list(scan.recommended_fixes),
            principles_enforced=[
                "security_first",
                "privacy_first",
                "verification_before_execution",
                "minimum_required_permissions",
                "human_approval_for_risky_actions",
                "full_audit_trail",
            ],
        )

    def sdk_input_guardrail(self, agent_entry: SaturnixAgentRegistryEntry):
        sdk = load_agents_sdk()
        if not sdk.available:
            return None

        @sdk.input_guardrail
        async def saturnix_input_guardrail(_ctx, _agent, input_data):  # pragma: no cover
            decision = self.evaluate(
                text=str(input_data),
                agent=agent_entry,
                dry_run=False,
                approved=False,
            )
            return sdk.GuardrailFunctionOutput(
                output_info=decision.model_dump(mode="json"),
                tripwire_triggered=not decision.allowed,
            )

        return saturnix_input_guardrail


def _has_risky_permission(agent: SaturnixAgentRegistryEntry) -> bool:
    risky = {
        PermissionLevel.memory_write,
        PermissionLevel.tool_execution,
        PermissionLevel.file_access,
        PermissionLevel.network_access,
        PermissionLevel.admin_security,
    }
    return any(permission in risky for permission in agent.permissions)


def _sensitivity(agent: SaturnixAgentRegistryEntry) -> str:
    if agent.memory_scope in {"personal", "voice", "system"}:
        return "sensitive"
    return "standard"
