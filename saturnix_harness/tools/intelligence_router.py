from __future__ import annotations

from dataclasses import dataclass

from saturnix_harness.schemas import ToolRoutingRequest, ToolRoutingResult


class ToolIntelligenceRouter:
    """SATURNIX tool selection brain.

    This router does not execute tools. It decides which tools are best suited
    for a task by scoring capability fit, speed, privacy, cost, reliability, and
    scalability.
    """

    def __init__(self, available_tools: list[str] | None = None) -> None:
        self.available_tools = set(available_tools or _TOOL_PROFILES)

    def route(self, request: ToolRoutingRequest) -> ToolRoutingResult:
        available = set(request.available_tools or self.available_tools)
        scored = [
            _score_tool(profile, request)
            for name, profile in _TOOL_PROFILES.items()
            if name in available
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        selected = [item.profile.name for item in scored if item.score >= 4][:4]
        if not selected and scored:
            selected = [scored[0].profile.name]
        fallback = [
            item.profile.name
            for item in scored
            if item.profile.name not in selected
        ][:3]
        reasoning = [
            _reason_for_selection(item, selected)
            for item in scored
            if item.profile.name in selected
        ]
        if not reasoning:
            reasoning = ["No available tool strongly matched; use human review before execution."]
        return ToolRoutingResult(
            selected_tools=selected,
            tool_reasoning=reasoning,
            fallback_tools=fallback,
        )


@dataclass(frozen=True)
class _ToolProfile:
    name: str
    keywords: set[str]
    speed: int
    privacy: int
    cost: int
    reliability: int
    scalability: int
    description: str


@dataclass(frozen=True)
class _ScoredTool:
    profile: _ToolProfile
    score: int
    reasons: list[str]


_TOOL_PROFILES: dict[str, _ToolProfile] = {
    "web_search": _ToolProfile(
        name="web_search",
        keywords={"web", "search", "latest", "current", "news", "external", "research"},
        speed=3,
        privacy=1,
        cost=4,
        reliability=2,
        scalability=3,
        description="Use for current public information and open-web discovery.",
    ),
    "apis": _ToolProfile(
        name="apis",
        keywords={"api", "integration", "service", "webhook", "request", "function"},
        speed=4,
        privacy=2,
        cost=3,
        reliability=4,
        scalability=5,
        description="Use for structured external system access and integrations.",
    ),
    "local_python": _ToolProfile(
        name="local_python",
        keywords={"python", "calculate", "parse", "script", "data", "transform", "test"},
        speed=5,
        privacy=5,
        cost=5,
        reliability=4,
        scalability=3,
        description="Use for private local computation, parsing, and deterministic checks.",
    ),
    "docker": _ToolProfile(
        name="docker",
        keywords={"docker", "container", "isolate", "sandbox", "service", "deploy"},
        speed=2,
        privacy=4,
        cost=3,
        reliability=5,
        scalability=5,
        description="Use for isolated execution, services, and reproducible environments.",
    ),
    "github": _ToolProfile(
        name="github",
        keywords={"github", "repo", "pull request", "issue", "commit", "branch", "ci"},
        speed=3,
        privacy=2,
        cost=4,
        reliability=4,
        scalability=4,
        description="Use for repository, issue, PR, branch, and CI workflows.",
    ),
    "databases": _ToolProfile(
        name="databases",
        keywords={"database", "sql", "sqlite", "postgres", "query", "table", "record"},
        speed=4,
        privacy=4,
        cost=4,
        reliability=5,
        scalability=5,
        description="Use for structured durable state and queryable records.",
    ),
    "file_systems": _ToolProfile(
        name="file_systems",
        keywords={"file", "folder", "path", "read", "write", "document", "workspace"},
        speed=5,
        privacy=5,
        cost=5,
        reliability=4,
        scalability=3,
        description="Use for local workspace files, documents, and controlled file access.",
    ),
    "vector_memory": _ToolProfile(
        name="vector_memory",
        keywords={"memory", "semantic", "recall", "context", "embedding", "history"},
        speed=5,
        privacy=4,
        cost=5,
        reliability=4,
        scalability=4,
        description="Use for semantic retrieval and long-term SATURNIX context.",
    ),
    "voice_systems": _ToolProfile(
        name="voice_systems",
        keywords={"voice", "speech", "audio", "transcribe", "tts", "stt", "microphone"},
        speed=4,
        privacy=2,
        cost=3,
        reliability=3,
        scalability=3,
        description="Use for speech-to-text, text-to-speech, and spoken commands.",
    ),
    "raspberry_pi_edge_node": _ToolProfile(
        name="raspberry_pi_edge_node",
        keywords={"raspberry", "edge", "sensor", "offline", "device", "iot", "local node"},
        speed=3,
        privacy=5,
        cost=4,
        reliability=3,
        scalability=3,
        description="Use for local edge execution, sensors, and offline node behavior.",
    ),
}


def _score_tool(profile: _ToolProfile, request: ToolRoutingRequest) -> _ScoredTool:
    text = _combined_text(request)
    score = 0
    reasons: list[str] = []
    keyword_hits = sorted(keyword for keyword in profile.keywords if keyword in text)
    if keyword_hits:
        score += 5 + min(4, len(keyword_hits))
        reasons.append(f"matches task keywords: {', '.join(keyword_hits[:4])}")

    score += _attribute_score(profile.speed, request.speed_requirement, "speed", reasons)
    score += _privacy_score(profile, request, reasons)
    score += _attribute_score(profile.cost, request.execution_cost, "cost", reasons)
    score += _attribute_score(
        profile.reliability,
        request.reliability_requirement,
        "reliability",
        reasons,
    )
    score += _attribute_score(
        profile.scalability,
        request.scalability_requirement,
        "scalability",
        reasons,
    )
    score += _constraint_score(profile, request.constraints, reasons)
    return _ScoredTool(profile=profile, score=score, reasons=reasons)


def _attribute_score(
    value: int,
    requirement: str,
    label: str,
    reasons: list[str],
) -> int:
    normalized = requirement.lower()
    if normalized in {"high", "fast", "low_latency", "strict"} and value >= 4:
        reasons.append(f"strong {label} fit")
        return 2
    if normalized in {"low", "cheap", "minimal"} and label == "cost" and value >= 4:
        reasons.append("low execution cost")
        return 2
    if normalized in {"medium", "normal", "standard", "balanced"} and value >= 3:
        return 1
    return 0


def _privacy_score(
    profile: _ToolProfile,
    request: ToolRoutingRequest,
    reasons: list[str],
) -> int:
    privacy = request.privacy_level.lower()
    if privacy in {"private", "local", "confidential", "restricted", "sensitive"}:
        if profile.privacy >= 4:
            reasons.append("keeps sensitive work local or controlled")
            return 4
        reasons.append("privacy penalty for external or less-controlled tool")
        return -4
    if profile.privacy >= 3:
        return 1
    return 0


def _constraint_score(
    profile: _ToolProfile,
    constraints: list[str],
    reasons: list[str],
) -> int:
    text = " ".join(constraints).lower()
    score = 0
    if "offline" in text or "no network" in text:
        offline_tools = {
            "local_python",
            "file_systems",
            "vector_memory",
            "raspberry_pi_edge_node",
        }
        if profile.name in offline_tools:
            reasons.append("works with offline or no-network constraint")
            score += 3
        elif profile.name in {"web_search", "apis", "github", "voice_systems"}:
            reasons.append("network dependency conflicts with offline constraint")
            score -= 4
    if "sandbox" in text and profile.name == "docker":
        reasons.append("sandbox requirement favors container isolation")
        score += 4
    if "semantic" in text and profile.name == "vector_memory":
        reasons.append("semantic retrieval constraint favors vector memory")
        score += 4
    return score


def _reason_for_selection(scored: _ScoredTool, selected: list[str]) -> str:
    status = "selected" if scored.profile.name in selected else "candidate"
    reasons = "; ".join(scored.reasons) if scored.reasons else scored.profile.description
    return f"{scored.profile.name} {status} with score {scored.score}: {reasons}."


def _combined_text(request: ToolRoutingRequest) -> str:
    return " ".join(
        [
            request.task,
            request.task_type,
            request.speed_requirement,
            request.privacy_level,
            request.execution_cost,
            request.reliability_requirement,
            request.scalability_requirement,
            " ".join(request.constraints),
        ]
    ).lower()
