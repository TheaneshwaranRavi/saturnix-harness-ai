from __future__ import annotations

from saturnix_harness.schemas import PermissionLevel, SaturnixAgentRegistryEntry


class SaturnixAgentRegistry:
    """Unified SATURNIX agent registry for SDK-backed orchestration."""

    def __init__(self) -> None:
        self._entries = {entry.agent_name: entry for entry in _default_entries()}

    def list(self) -> list[SaturnixAgentRegistryEntry]:
        return list(self._entries.values())

    def get(self, agent_name: str) -> SaturnixAgentRegistryEntry | None:
        return self._entries.get(agent_name)

    def require(self, agent_name: str) -> SaturnixAgentRegistryEntry:
        entry = self.get(agent_name)
        if not entry:
            raise KeyError(f"Unknown SATURNIX SDK agent: {agent_name}")
        return entry


def _default_entries() -> list[SaturnixAgentRegistryEntry]:
    return [
        _entry(
            "Personal Assistant Agent",
            "Coordinate personal SATURNIX assistance, planning, reminders, and safe delegation.",
            "GPT",
            [PermissionLevel.read_only, PermissionLevel.memory_write],
            ["memory_search_tool", "workflow_tool", "security_scan_tool"],
            "LOW",
            "personal",
            "Coordinate the user's SATURNIX operating tasks with concise, practical guidance.",
            ["Memory Agent", "Workflow Agent"],
        ),
        _entry(
            "Coding Agent",
            "Build, debug, refactor, and verify code with tool-scoped permissions.",
            "GPT",
            [PermissionLevel.read_only, PermissionLevel.tool_execution],
            ["memory_search_tool", "code_execution_tool", "security_scan_tool"],
            "MEDIUM",
            "project",
            "Produce type-safe, modular software changes and explain verification clearly.",
            ["Security Agent", "Verification Agent", "Memory Agent"],
        ),
        _entry(
            "Research Agent",
            "Analyze documents, collect context, and synthesize grounded findings.",
            "Claude",
            [PermissionLevel.read_only, PermissionLevel.network_access],
            ["web_search_tool", "memory_search_tool", "security_scan_tool"],
            "LOW",
            "project",
            "Return sourced, careful research summaries and identify uncertainty explicitly.",
            ["Coding Agent", "Memory Agent"],
        ),
        _entry(
            "Security Agent",
            "Detect prompt injection, unsafe workflows, suspicious files, and secret exposure.",
            "GPT",
            [PermissionLevel.read_only, PermissionLevel.admin_security],
            ["security_scan_tool", "memory_search_tool"],
            "HIGH",
            "system",
            "Enforce zero-trust safety, block dangerous actions, and recommend mitigations.",
            ["Verification Agent"],
        ),
        _entry(
            "Memory Agent",
            "Save, search, compress, and protect long-term SATURNIX memory.",
            "Gemma via Ollama",
            [PermissionLevel.read_only, PermissionLevel.memory_write],
            ["memory_search_tool", "security_scan_tool"],
            "MEDIUM",
            "segmented",
            "Store only useful, approved, classified memory and avoid raw secrets.",
            [],
        ),
        _entry(
            "Workflow Agent",
            "Plan dependency-aware workflows and coordinate execution order.",
            "Gemini",
            [PermissionLevel.read_only, PermissionLevel.tool_execution],
            ["workflow_tool", "memory_search_tool", "security_scan_tool"],
            "MEDIUM",
            "project",
            "Break goals into verifiable steps with safe handoffs and rollback notes.",
            ["Security Agent", "Coding Agent", "Memory Agent"],
        ),
        _entry(
            "Voice Agent",
            "Route voice commands through STT, intent analysis, confirmation, and TTS.",
            "Groq",
            [PermissionLevel.read_only, PermissionLevel.tool_execution],
            ["voice_transcription_tool", "workflow_tool", "security_scan_tool"],
            "HIGH",
            "voice",
            "Handle conversational commands with low latency and confirmation for risky actions.",
            ["Research Agent"],
        ),
        _entry(
            "Raspberry Pi Edge Agent",
            "Coordinate Raspberry Pi edge node health, queues, and signed automation commands.",
            "Gemma via Ollama",
            [PermissionLevel.read_only, PermissionLevel.tool_execution],
            ["edge_node_tool", "security_scan_tool"],
            "HIGH",
            "edge",
            "Dispatch only signed, validated edge commands and preserve audit receipts.",
            ["Security Agent"],
        ),
        _entry(
            "Job Application Agent",
            "Create verified job application assets from approved user memory.",
            "GPT",
            [PermissionLevel.read_only, PermissionLevel.memory_write],
            ["memory_search_tool", "web_search_tool", "security_scan_tool"],
            "MEDIUM",
            "personal",
            "Draft truthful, tailored application material and separate evidence from inference.",
            ["Research Agent", "Verification Agent"],
        ),
        _entry(
            "Semiconductor Design Agent",
            "Analyze semiconductor, EDA, embedded, and hardware engineering tasks.",
            "Claude",
            [PermissionLevel.read_only],
            ["memory_search_tool", "web_search_tool", "security_scan_tool"],
            "MEDIUM",
            "project",
            "Reason carefully about semiconductor workflows, constraints, and verification steps.",
            ["Research Agent", "Coding Agent"],
        ),
        _entry(
            "Verification Agent",
            "Validate outputs before execution, memory writes, or user-facing delivery.",
            "GPT",
            [PermissionLevel.read_only],
            ["security_scan_tool", "memory_search_tool"],
            "MEDIUM",
            "system",
            "Check requirements, uncertainty, security, hallucination risk, and next actions.",
            ["Memory Agent"],
        ),
    ]


def _entry(
    name: str,
    purpose: str,
    brain: str,
    permissions: list[PermissionLevel],
    tools: list[str],
    risk: str,
    memory_scope: str,
    instructions: str,
    handoffs: list[str],
) -> SaturnixAgentRegistryEntry:
    return SaturnixAgentRegistryEntry(
        agent_name=name,
        purpose=purpose,
        best_brain=brain,
        permissions=_minimum_permissions(permissions),
        tools=tools,
        risk_level=risk,  # type: ignore[arg-type]
        memory_scope=memory_scope,
        instructions=(
            "You are a SATURNIX-HARNESS infrastructure agent, not a chatbot. "
            "Operate security-first, privacy-first, verification-first, and keep an audit trail. "
            f"{instructions}"
        ),
        guardrails=[
            "prompt injection detection",
            "dangerous tool blocking",
            "unsafe code execution blocking",
            "unauthorized file access blocking",
            "secret exposure prevention",
            "human approval for risky actions",
        ],
        fallback_logic=[
            "fallback to Ollama when OpenAI Agents SDK is unavailable",
            "fallback to Gemma for local/private lightweight work",
            "fallback to local coding model for code tasks",
            "return structured blocked result when guardrails trip",
        ],
        handoffs=handoffs,
        tracing_enabled=True,
    )


def _minimum_permissions(permissions: list[PermissionLevel]) -> list[PermissionLevel]:
    ordered = []
    for permission in permissions:
        if permission not in ordered:
            ordered.append(permission)
    if PermissionLevel.read_only not in ordered:
        ordered.insert(0, PermissionLevel.read_only)
    return ordered
