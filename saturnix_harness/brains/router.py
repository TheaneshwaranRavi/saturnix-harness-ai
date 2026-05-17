from __future__ import annotations

import logging

from saturnix_harness.brains.base import BrainProvider
from saturnix_harness.brains.claude_provider import ClaudeProvider
from saturnix_harness.brains.gemini_provider import GeminiProvider
from saturnix_harness.brains.groq_provider import GroqProvider
from saturnix_harness.brains.mock_provider import MockProvider
from saturnix_harness.brains.ollama_provider import build_ollama_coding, build_ollama_gemma
from saturnix_harness.brains.openai_provider import OpenAIProvider
from saturnix_harness.config import Settings
from saturnix_harness.exceptions import BrainProviderError, RoutingError
from saturnix_harness.schemas import (
    BrainName,
    BrainRouteRequest,
    BrainRouteResponse,
    BrainRequest,
    BrainResponse,
    Capability,
    ProviderHealth,
    RoutingDecision,
)

logger = logging.getLogger(__name__)


class BrainRouter:
    """Resource and brain routing layer.

    The router scores providers by capability fit, local/privacy requirements, and
    preferred provider hints. It falls back gracefully so construction workflows can
    keep moving when a paid API is not configured yet.
    """

    def __init__(
        self,
        settings: Settings,
        providers: list[BrainProvider] | None = None,
    ) -> None:
        self.settings = settings
        self.providers: dict[BrainName, BrainProvider] = {
            provider.name: provider for provider in (providers or self._build_default_providers())
        }

    def _build_default_providers(self) -> list[BrainProvider]:
        providers: list[BrainProvider] = [
            OpenAIProvider(self.settings),
            ClaudeProvider(self.settings),
            GeminiProvider(self.settings),
            build_ollama_gemma(self.settings),
            build_ollama_coding(self.settings),
            GroqProvider(self.settings),
        ]
        if self.settings.saturnix_enable_mock_brains:
            providers.append(MockProvider(model="saturnix-mock-v1", enabled=True))
        return providers

    async def health(self) -> list[ProviderHealth]:
        return [await provider.health() for provider in self.providers.values()]

    def register(self, provider: BrainProvider) -> None:
        self.providers[provider.name] = provider

    def route_task(self, request: BrainRouteRequest) -> BrainRouteResponse:
        """Select the best SATURNIX brain for a high-level task description.

        Input and output match the public SATURNIX Brain Router JSON contract:

        {
          "task": "",
          "task_type": "",
          "privacy_level": "",
          "speed_priority": "",
          "context_size": "",
          "output_format": ""
        }
        """

        normalized = _normalize_route_request(request)

        if _is_voice_task(normalized):
            return BrainRouteResponse(
                selected_brain="Groq",
                reason="Task requires speech-to-text, text-to-speech, or voice interaction.",
                fallback_brain="GPT",
                execution_strategy=(
                    "Use Groq for voice/audio processing, then hand the transcript or response "
                    "to GPT for reasoning if deeper orchestration is needed."
                ),
            )

        if _requires_private_local_execution(normalized):
            if _is_coding_task(normalized):
                return BrainRouteResponse(
                    selected_brain="MiniMax/Coding via Ollama",
                    reason="Task is private/local and coding-oriented, so fast local coding is preferred.",
                    fallback_brain="Gemma via Ollama",
                    execution_strategy=(
                        "Run the coding model through Ollama locally. Fall back to Gemma via Ollama "
                        "for lightweight private reasoning if the coding model is unavailable."
                    ),
                )
            return BrainRouteResponse(
                selected_brain="Gemma via Ollama",
                reason="Privacy level requires local/private execution for a lightweight task.",
                fallback_brain="MiniMax/Coding via Ollama",
                execution_strategy=(
                    "Run Gemma locally through Ollama. Keep prompts, context, and outputs on-device."
                ),
            )

        if _needs_structured_output(normalized):
            return BrainRouteResponse(
                selected_brain="Gemini",
                reason="Task asks for structured JSON, function calling, or schema-based output.",
                fallback_brain="GPT",
                execution_strategy=(
                    "Use Gemini with an explicit JSON schema or function declaration. Validate the "
                    "response before passing it to execution tools."
                ),
            )

        if _needs_large_context(normalized):
            return BrainRouteResponse(
                selected_brain="Claude",
                reason="Task requires long document handling, deep analysis, or a large context window.",
                fallback_brain="GPT",
                execution_strategy=(
                    "Use Claude for document/context analysis. Summarize findings into compact "
                    "handoff notes for downstream planning or execution."
                ),
            )

        if _is_fast_local_coding(normalized):
            return BrainRouteResponse(
                selected_brain="MiniMax/Coding via Ollama",
                reason="Task is coding-oriented and speed priority favors a fast local coding model.",
                fallback_brain="GPT",
                execution_strategy=(
                    "Use the local Ollama coding model for fast draft code, then optionally verify "
                    "with GPT for architecture and correctness."
                ),
            )

        return BrainRouteResponse(
            selected_brain="GPT",
            reason="Task is best matched to reasoning, coding, architecture, or planning.",
            fallback_brain="Claude",
            execution_strategy=(
                "Use GPT as the primary reasoning and planning brain. Fall back to Claude when "
                "context grows large or deeper document analysis is required."
            ),
        )

    def route(self, request: BrainRequest) -> RoutingDecision:
        required = request.required_capabilities
        local_only = request.local_only or self.settings.saturnix_local_only
        candidates = [provider for provider in self.providers.values() if provider.enabled]
        if local_only:
            candidates = [provider for provider in candidates if Capability.local_private in provider.capabilities]
        capable = [provider for provider in candidates if provider.can_satisfy(required)]
        if not capable:
            capable = [
                provider
                for provider in candidates
                if not required or set(required).intersection(provider.capabilities)
            ]
        if not capable:
            raise RoutingError(f"No enabled brain can satisfy capabilities: {required}")

        scored = sorted(
            capable,
            key=lambda provider: self._score_provider(provider, request),
            reverse=True,
        )
        selected = scored[0]
        fallback_chain = [provider.name for provider in scored[1:]]
        return RoutingDecision(
            selected=selected.name,
            model=selected.model,
            reason=self._decision_reason(selected, request),
            fallback_chain=fallback_chain,
        )

    async def complete(self, request: BrainRequest) -> BrainResponse:
        decision = self.route(request)
        provider_order = [decision.selected, *decision.fallback_chain]
        last_error: Exception | None = None
        for provider_name in provider_order:
            provider = self.providers[provider_name]
            try:
                return await provider.timed_complete(request)
            except BrainProviderError as exc:
                last_error = exc
                logger.warning("Brain provider %s failed: %s", provider_name, exc)
            except Exception as exc:  # pragma: no cover - defensive adapter boundary
                last_error = exc
                logger.exception("Unexpected brain provider failure from %s", provider_name)
        raise BrainProviderError(f"All routed providers failed: {last_error}") from last_error

    def _score_provider(self, provider: BrainProvider, request: BrainRequest) -> int:
        score = 0
        score += 10 * len(set(request.required_capabilities).intersection(provider.capabilities))
        if provider.name == request.preferred_brain:
            score += 50
        if Capability.local_private in provider.capabilities and (request.local_only or self.settings.saturnix_local_only):
            score += 40
        if provider.name.value == self.settings.saturnix_default_brain:
            score += 5
        if provider.name == BrainName.mock:
            score -= 20
        if not provider.enabled:
            score -= 1000
        return score

    def _decision_reason(self, provider: BrainProvider, request: BrainRequest) -> str:
        matched = sorted(
            {capability.value for capability in request.required_capabilities if capability in provider.capabilities}
        )
        if provider.name == request.preferred_brain:
            return "preferred brain matched requested capabilities"
        if matched:
            return f"matched capabilities: {', '.join(matched)}"
        return "best available enabled fallback"


def _normalize_route_request(request: BrainRouteRequest) -> dict[str, str]:
    return {
        "task": request.task.lower().strip(),
        "task_type": request.task_type.lower().strip(),
        "privacy_level": request.privacy_level.lower().strip(),
        "speed_priority": request.speed_priority.lower().strip(),
        "context_size": request.context_size.lower().strip(),
        "output_format": request.output_format.lower().strip(),
        "combined": " ".join(
            [
                request.task,
                request.task_type,
                request.privacy_level,
                request.speed_priority,
                request.context_size,
                request.output_format,
            ]
        )
        .lower()
        .strip(),
    }


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _is_voice_task(values: dict[str, str]) -> bool:
    return _contains_any(
        values["combined"],
        {
            "speech",
            "voice",
            "audio",
            "transcribe",
            "transcription",
            "text-to-speech",
            "tts",
            "speech-to-text",
            "stt",
            "realtime",
            "real-time",
        },
    )


def _requires_private_local_execution(values: dict[str, str]) -> bool:
    return _contains_any(
        values["privacy_level"] + " " + values["combined"],
        {"private", "local", "offline", "confidential", "sensitive", "on-device", "on device"},
    )


def _is_coding_task(values: dict[str, str]) -> bool:
    return _contains_any(
        values["task_type"] + " " + values["task"],
        {
            "code",
            "coding",
            "programming",
            "debug",
            "bug",
            "refactor",
            "python",
            "typescript",
            "javascript",
            "api",
            "test",
        },
    )


def _needs_structured_output(values: dict[str, str]) -> bool:
    return _contains_any(
        values["output_format"] + " " + values["task_type"] + " " + values["task"],
        {
            "json",
            "schema",
            "structured",
            "function",
            "function calling",
            "tool call",
            "tool-call",
            "pydantic",
        },
    )


def _needs_large_context(values: dict[str, str]) -> bool:
    context_size = values["context_size"]
    if context_size.isdigit() and int(context_size) >= 50000:
        return True
    return _contains_any(
        values["combined"],
        {
            "large context",
            "long context",
            "long document",
            "long documents",
            "document",
            "documents",
            "deep analysis",
            "deep research",
            "contract",
            "pdf",
            "book",
            "large",
            "huge",
        },
    )


def _is_fast_local_coding(values: dict[str, str]) -> bool:
    return _is_coding_task(values) and _contains_any(
        values["speed_priority"],
        {"high", "fast", "realtime", "real-time", "low latency", "quick"},
    )
