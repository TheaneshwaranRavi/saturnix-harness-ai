from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from saturnix_harness.config import Settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.dashboard.crypto import SecretCipher
from saturnix_harness.dashboard.data_guardian import DataGuardian
from saturnix_harness.dashboard.doctrine import SaturnixOperatingDoctrine
from saturnix_harness.dashboard.security import DashboardSecuritySentinel
from saturnix_harness.schemas import (
    ApiKeyStoreRequest,
    CreateDashboardAgentRequest,
    DataGuardianClassifyRequest,
    DashboardAgentDefinition,
    DashboardMemorySaveRequest,
    DashboardMemorySearchRequest,
    DashboardSecurityScanRequest,
    DashboardWorkflowRunRequest,
    ExecuteDashboardAgentRequest,
    MemoryType,
    PermissionLevel,
    SaturnixExecutionRequest,
    SaveMemoryRequest,
    SearchMemoryRequest,
    UserProfile,
)


class DashboardService:
    """Application service for the personalized SATURNIX infrastructure dashboard."""

    def __init__(self, orchestrator: CoreOrchestrator) -> None:
        self.orchestrator = orchestrator
        self.settings: Settings = orchestrator.settings
        self.security = DashboardSecuritySentinel()
        self.data_guardian = DataGuardian(self.settings)
        self.doctrine = SaturnixOperatingDoctrine()
        self.cipher = SecretCipher(self.settings)
        self._custom_agents: dict[str, DashboardAgentDefinition] = {}
        self._api_keys: dict[str, dict[str, Any]] = {}
        self.lockdown_mode = self.settings.saturnix_lockdown_mode

    async def overview(self) -> dict[str, Any]:
        health = await self.orchestrator.brain_router.health()
        agents = self.agents()
        security = self.security_status()
        return {
            "model_name": "SATURNIX-HARNESS",
            "purpose": (
                "Personal AI infrastructure system for constructing, managing, "
                "securing, verifying, and scaling agentic AI systems."
            ),
            "operating_doctrine": self.doctrine.summary(),
            "core_control_center": "MacBook Air M1",
            "edge_node": "Raspberry Pi 4B+",
            "storage": {
                "fast_memory": "External SSD",
                "vault": "HDD / 10TB storage",
                "recovery": "optional pendrives",
            },
            "system_health": {
                "status": "lockdown" if self.lockdown_mode else "operational",
                "brain_providers": [item.model_dump(mode="json") for item in health],
                "agents_online": len(agents),
                "security_score": security["security_score"],
                "agents_sdk": self.orchestrator.sdk_agent_manager.sdk_status(),
            },
            "live_metrics": {
                "active_workflows": 3,
                "memory_records": len(self.orchestrator.memory.list(namespace=None, limit=100)),
                "audit_events": len(self.audit_logs()),
                "voice_status": self.voice_status()["status"],
                "trace_events": len(self.orchestrator.sdk_agent_manager.trace_summary().events),
            },
            "topology": [
                {"source": "Dashboard", "target": "SATURNIX Core"},
                {"source": "SATURNIX Core", "target": "Brain Router"},
                {"source": "SATURNIX Core", "target": "Raspberry Pi Edge Node"},
                {"source": "SATURNIX Core", "target": "Memory Vault"},
                {"source": "Brain Router", "target": "Cloud APIs"},
                {"source": "Voice Console", "target": "Groq STT/TTS"},
            ],
        }

    def agents(self) -> list[DashboardAgentDefinition]:
        agents = {agent.name: agent for agent in _default_agents()}
        agents.update(self._custom_agents)
        return list(agents.values())

    def create_agent(self, request: CreateDashboardAgentRequest) -> DashboardAgentDefinition:
        agent = DashboardAgentDefinition(
            name=request.name,
            agent_name=request.name,
            purpose=request.purpose,
            best_brain=request.best_brain,
            tools=request.tools,
            permissions=_minimum_permissions(request.permissions),
            memory_access_level=request.memory_access_level,
            risk_level=request.risk_level,
            validation_rules=request.validation_rules or ["verify output before execution"],
        )
        self._custom_agents[agent.name] = agent
        self.audit("agent.create", {"agent": agent.name, "permissions": agent.permissions})
        return agent

    async def execute_agent(self, request: ExecuteDashboardAgentRequest) -> dict[str, Any]:
        if self.lockdown_mode:
            return {"ok": False, "blocked": True, "reason": "Emergency lockdown mode is active."}
        agent = next((item for item in self.agents() if item.name == request.agent_name), None)
        if not agent:
            return {"ok": False, "error": f"Unknown agent: {request.agent_name}"}
        scan = self.security.scan(
            DashboardSecurityScanRequest(
                input_text=f"{request.goal}\n{request.context or ''}",
                source=f"agent:{agent.name}",
            )
        )
        classification = self.data_guardian.classify(
            DataGuardianClassifyRequest(
                content=f"{request.goal}\n{request.context or ''}",
                intended_action="agent_execute",
            )
        )
        preflight = self.doctrine.preflight_agent_execution(
            agent=agent,
            security=scan,
            classification=classification,
            dry_run=request.dry_run,
            approved=request.approved,
        )
        if not preflight["allowed"]:
            self.audit(
                "agent.execute.blocked",
                {
                    "agent": agent.name,
                    "security": scan.model_dump(mode="json"),
                    "doctrine": preflight,
                },
            )
            return {
                "ok": False,
                "confirmation_required": preflight["approval_required"],
                "security": scan.model_dump(mode="json"),
                "classification": classification.model_dump(mode="json"),
                "doctrine": preflight,
            }
        if request.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "agent": agent.model_dump(mode="json"),
                "security": scan.model_dump(mode="json"),
                "classification": classification.model_dump(mode="json"),
                "doctrine": preflight,
            }
        result = await self.orchestrator.execute_goal(
            SaturnixExecutionRequest(
                goal=request.goal,
                input=request.context,
                task_type=agent.purpose,
                privacy_level="standard",
                output_format="markdown",
                metadata={"dashboard_agent": agent.name},
            )
        )
        self.audit("agent.execute", {"agent": agent.name, "goal": request.goal})
        return {"ok": True, "doctrine": preflight, "result": result.model_dump(mode="json")}

    async def brains(self) -> list[dict[str, Any]]:
        health = await self.orchestrator.brain_router.health()
        return [item.model_dump(mode="json") for item in health]

    def memory(self) -> list[dict[str, Any]]:
        return [
            record.model_dump(mode="json")
            for record in self.orchestrator.memory.list(namespace=None, limit=50)
        ]

    def save_memory(self, request: DashboardMemorySaveRequest) -> dict[str, Any]:
        classification = self.data_guardian.classify(
            DataGuardianClassifyRequest(
                content=request.content,
                intended_action="memory_save",
            )
        )
        if classification.blocked_actions or not request.user_permission:
            return {
                "ok": False,
                "blocked_actions": classification.blocked_actions
                or ["User permission is required before storing memory."],
            }
        content, metadata = self.data_guardian.encrypt_if_sensitive(
            request.content,
            classification,
        )
        record = self.orchestrator.memory.save_memory(
            SaveMemoryRequest(
                content=content,
                memory_type=request.memory_type,
                namespace=request.namespace,
                kind="dashboard_memory",
                title=request.title,
                tags=[*request.tags, classification.data_class.value],
                metadata=metadata,
                source="dashboard",
            )
        )
        self.audit("memory.save", {"record_id": record.id, "namespace": request.namespace})
        return {
            "ok": True,
            "record": record.model_dump(mode="json"),
            "classification": classification.model_dump(mode="json"),
        }

    def search_memory(self, request: DashboardMemorySearchRequest) -> list[dict[str, Any]]:
        records = self.orchestrator.memory.search_memory(
            SearchMemoryRequest(
                query=request.query,
                namespace=request.namespace,
                limit=request.limit,
            )
        )
        self.audit("memory.search", {"query": request.query, "namespace": request.namespace})
        return [record.model_dump(mode="json") for record in records]

    def security_status(self) -> dict[str, Any]:
        result = self.security.scan(DashboardSecurityScanRequest(input_text="routine status check"))
        return {
            **result.model_dump(mode="json"),
            "lockdown_mode": self.lockdown_mode,
            "zero_trust": True,
            "operating_doctrine": self.doctrine.summary(),
            "security_controls": [
                "JWT authentication middleware",
                "role-based access control",
                "audit logging",
                "rate limiting",
                "secure headers",
                "prompt injection detection",
                "path traversal blocking",
                "encrypted API key storage",
            ],
        }

    def scan_input(self, request: DashboardSecurityScanRequest) -> dict[str, Any]:
        result = self.security.scan(request)
        if result.lockdown_required:
            self.lockdown_mode = True
        self.audit("security.scan", result.model_dump(mode="json"))
        return result.model_dump(mode="json")

    def lockdown(self) -> dict[str, Any]:
        self.lockdown_mode = True
        self.audit("security.lockdown", {"lockdown_mode": True})
        return {
            "lockdown_mode": True,
            "actions": [
                "tool execution stopped",
                "external API calls disabled",
                "memory writes frozen for sensitive classes",
                "file access blocked except audit logging",
                "incident log created",
            ],
        }

    def operating_doctrine(self) -> dict[str, Any]:
        return self.doctrine.summary()

    def agent_registry(self) -> dict[str, Any]:
        return {
            "sdk_status": self.orchestrator.sdk_agent_manager.sdk_status(),
            "agents": [
                agent.model_dump(mode="json")
                for agent in self.orchestrator.sdk_agent_manager.registry_entries()
            ],
            "handoff_plan": self.orchestrator.sdk_agent_manager.handoff_plan().model_dump(
                mode="json"
            ),
        }

    def traces(self, limit: int = 100) -> dict[str, Any]:
        return self.orchestrator.sdk_agent_manager.trace_summary(limit=limit).model_dump(
            mode="json"
        )

    def edge_status(self) -> dict[str, Any]:
        return {
            "node": "Raspberry Pi 4B+",
            "role": "SATURNIX Edge Node",
            "status": "configured",
            "heartbeat": "pending real device integration",
            "capabilities": ["GPIO automation", "offline queue", "sensor intake", "edge scripts"],
            "security": ["signed commands", "least privilege", "local queue replay"],
        }

    def storage_status(self) -> dict[str, Any]:
        return self.data_guardian.storage_status()

    def workflows(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "secure-agent-build",
                "status": "ready",
                "risk_level": "MEDIUM",
                "steps": ["intent", "agents", "routing", "execution", "verification"],
            },
            {
                "name": "voice-command-routing",
                "status": "ready",
                "risk_level": "HIGH",
                "steps": ["stt", "intent", "confirmation", "execution", "tts"],
            },
            {
                "name": "memory-vault-backup",
                "status": "planned",
                "risk_level": "LOW",
                "steps": ["classify", "encrypt", "snapshot", "checksum", "audit"],
            },
        ]

    async def run_workflow(self, request: DashboardWorkflowRunRequest) -> dict[str, Any]:
        if self.lockdown_mode:
            return {"ok": False, "blocked": True, "reason": "Emergency lockdown mode is active."}
        if request.requires_confirmation and not request.dry_run and not request.approved:
            return {
                "ok": False,
                "confirmation_required": True,
                "reason": "Zero trust requires confirmation before workflow execution.",
                "doctrine": self.doctrine.summary(),
            }
        if request.dry_run:
            return {"ok": True, "dry_run": True, "workflow": request.workflow_name}
        result = await self.orchestrator.execute_goal(SaturnixExecutionRequest(goal=request.goal))
        return {"ok": True, "result": result.model_dump(mode="json")}

    def voice_status(self) -> dict[str, Any]:
        return {
            "status": "configured" if self.settings.groq_api_key else "missing_groq_api_key",
            "provider": "Groq",
            "stt_model": self.settings.groq_transcription_model,
            "tts_model": self.settings.groq_tts_model,
            "low_latency_mode": True,
        }

    def logs(self) -> list[dict[str, Any]]:
        return [
            event.model_dump(mode="json")
            for event in self.orchestrator.monitoring.recent(limit=100)
        ]

    def audit_logs(self) -> list[dict[str, Any]]:
        records = self.orchestrator.memory.search_memory(
            SearchMemoryRequest(
                query="",
                namespace="dashboard:audit",
                memory_type=MemoryType.agent_execution_logs,
                limit=100,
                include_vector=False,
            )
        )
        return [record.model_dump(mode="json") for record in records]

    def store_api_key(self, request: ApiKeyStoreRequest) -> dict[str, Any]:
        encrypted = self.cipher.encrypt(request.api_key)
        key_id = str(uuid4())
        self._api_keys[key_id] = {
            "id": key_id,
            "provider": request.provider,
            "label": request.label,
            "encrypted": encrypted,
            "created_at": _now(),
        }
        self.audit("api_key.store", {"provider": request.provider, "label": request.label})
        return {
            "id": key_id,
            "provider": request.provider,
            "label": request.label,
            "stored_encrypted": True,
            "preview": _preview_secret(request.api_key),
        }

    def api_keys(self) -> list[dict[str, Any]]:
        return [
            {
                "id": item["id"],
                "provider": item["provider"],
                "label": item["label"],
                "stored_encrypted": True,
                "created_at": item["created_at"],
            }
            for item in self._api_keys.values()
        ]

    def user_profile(self) -> dict[str, Any]:
        return UserProfile().model_dump(mode="json")

    def audit(self, action: str, metadata: dict[str, Any]) -> None:
        redacted = _redact_metadata(metadata)
        self.orchestrator.memory.save_memory(
            SaveMemoryRequest(
                content=f"{action}: {redacted}",
                memory_type=MemoryType.agent_execution_logs,
                namespace="dashboard:audit",
                kind="audit_log",
                title=action,
                tags=["audit", "dashboard", action.split(".")[0]],
                metadata={"action": action, "metadata": redacted},
                source="dashboard",
            )
        )


def _default_agents() -> list[DashboardAgentDefinition]:
    return [
        _agent(
            "Personal Assistant Agent",
            "Coordinate daily SATURNIX assistance.",
            "GPT",
            ["memory_search"],
            [PermissionLevel.read_only, PermissionLevel.memory_write],
            "personal",
            "LOW",
        ),
        _agent(
            "Coding Agent",
            "Build, debug, and verify software systems.",
            "GPT",
            ["code_search", "test_runner"],
            [PermissionLevel.read_only, PermissionLevel.tool_execution],
            "project",
            "MEDIUM",
        ),
        _agent(
            "Research Agent",
            "Analyze sources and synthesize grounded research.",
            "Claude",
            ["document_parser", "memory_search"],
            [PermissionLevel.read_only, PermissionLevel.network_access],
            "project",
            "LOW",
        ),
        _agent(
            "Security Agent",
            "Detect threats and enforce zero-trust controls.",
            "GPT",
            ["security_scan", "audit_logs"],
            [PermissionLevel.read_only, PermissionLevel.admin_security],
            "system",
            "HIGH",
        ),
        _agent(
            "Memory Agent",
            "Maintain safe long-term user and system memory.",
            "Gemma via Ollama",
            ["memory_search", "memory_save"],
            [PermissionLevel.read_only, PermissionLevel.memory_write],
            "segmented",
            "MEDIUM",
        ),
        _agent(
            "Workflow Agent",
            "Plan and run validated automation workflows.",
            "Gemini",
            ["workflow_runner"],
            [PermissionLevel.read_only, PermissionLevel.tool_execution],
            "project",
            "MEDIUM",
        ),
        _agent(
            "Voice Agent",
            "Handle Groq voice commands and confirmations.",
            "Groq",
            ["stt", "tts"],
            [PermissionLevel.read_only, PermissionLevel.tool_execution],
            "voice",
            "HIGH",
        ),
        _agent(
            "Raspberry Pi Edge Agent",
            "Coordinate edge automation safely.",
            "Gemma via Ollama",
            ["edge_queue"],
            [PermissionLevel.read_only, PermissionLevel.tool_execution],
            "edge",
            "HIGH",
        ),
        _agent(
            "Job Application Agent",
            "Create verified career materials.",
            "GPT",
            ["memory_search"],
            [PermissionLevel.read_only, PermissionLevel.memory_write],
            "personal",
            "MEDIUM",
        ),
        _agent(
            "Semiconductor Design Agent",
            "Analyze semiconductor and EDA tasks.",
            "Claude",
            ["document_parser"],
            [PermissionLevel.read_only],
            "project",
            "MEDIUM",
        ),
    ]


def _agent(
    name: str,
    purpose: str,
    brain: str,
    tools: list[str],
    permissions: list[PermissionLevel],
    memory: str,
    risk: str,
) -> DashboardAgentDefinition:
    return DashboardAgentDefinition(
        name=name,
        agent_name=_phase1_agent_name(name),
        purpose=purpose,
        best_brain=brain,
        tools=tools,
        permissions=_minimum_permissions(permissions),
        memory_access_level=memory,
        risk_level=risk,  # type: ignore[arg-type]
        validation_rules=[
            "validate input before execution",
            "apply least privilege",
            "verify output before memory write",
        ],
    )


def _phase1_agent_name(name: str) -> str:
    return {
        "Personal Assistant Agent": "Automation Agent",
        "Security Agent": "Verification Agent",
        "Workflow Agent": "Automation Agent",
        "Raspberry Pi Edge Agent": "Automation Agent",
        "Job Application Agent": "Research Agent",
        "Semiconductor Design Agent": "Research Agent",
    }.get(name, name)


def _minimum_permissions(permissions: list[PermissionLevel]) -> list[PermissionLevel]:
    ordered = []
    for permission in permissions:
        if permission not in ordered:
            ordered.append(permission)
    if PermissionLevel.read_only not in ordered:
        ordered.insert(0, PermissionLevel.read_only)
    return ordered


def _redact_metadata(metadata: Any) -> Any:
    text = str(metadata)
    if any(marker in text.lower() for marker in {"api_key", "secret", "token", "password"}):
        return {"redacted": True, "reason": "sensitive metadata suppressed"}
    return metadata


def _preview_secret(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}...{value[-3:]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
