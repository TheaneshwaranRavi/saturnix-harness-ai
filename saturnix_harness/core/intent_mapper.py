from __future__ import annotations

from saturnix_harness.schemas import Capability, HarnessRequest, IntentMap


class HumanIntentMapper:
    """H: Human Intent Mapping."""

    def map(self, request: HarnessRequest) -> IntentMap:
        text = f"{request.goal}\n{request.input or ''}".lower()
        capabilities = set(request.required_capabilities)
        domain = "general"
        expected_outputs = ["actionable response"]
        constraints: list[str] = []

        if any(word in text for word in ["code", "api", "python", "fastapi", "class", "test"]):
            capabilities.update({Capability.coding, Capability.reasoning})
            domain = "software"
            expected_outputs.extend(["implementation guidance", "test strategy"])
        if any(word in text for word in ["plan", "architecture", "design", "orchestrate", "multi-agent"]):
            capabilities.update({Capability.planning, Capability.orchestration, Capability.reasoning})
            domain = "agentic_systems"
            expected_outputs.append("modular architecture")
        if any(word in text for word in ["document", "pdf", "contract", "long-context", "long context"]):
            capabilities.update({Capability.long_context, Capability.document_understanding})
            domain = "document_analysis"
        if any(word in text for word in ["json", "schema", "structured", "function call"]):
            capabilities.update({Capability.structured_output, Capability.function_calling})
            expected_outputs.append("structured output")
        if any(word in text for word in ["voice", "speech", "audio", "transcribe", "realtime"]):
            capabilities.update({Capability.voice, Capability.realtime_speech})
            domain = "voice"
        if any(word in text for word in ["private", "local", "offline", "ollama"]):
            capabilities.add(Capability.local_private)
            constraints.append("prefer local/private execution")

        if request.local_only:
            capabilities.add(Capability.local_private)
            constraints.append("local-only execution requested")

        summary = request.goal.strip()
        if request.input:
            summary += f" | Input context length: {len(request.input)} characters"

        return IntentMap(
            original_goal=request.goal,
            summary=summary,
            domain=domain,
            expected_outputs=sorted(set(expected_outputs)),
            constraints=constraints,
            required_capabilities=sorted(capabilities, key=lambda capability: capability.value),
            local_only=request.local_only,
        )

