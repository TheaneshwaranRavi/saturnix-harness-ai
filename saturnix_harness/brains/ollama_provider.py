from __future__ import annotations

import logging

import httpx

from saturnix_harness.brains.base import BrainProvider
from saturnix_harness.config import Settings
from saturnix_harness.exceptions import BrainProviderError
from saturnix_harness.schemas import (
    BrainName,
    BrainRequest,
    BrainResponse,
    Capability,
    OllamaGenerationResult,
    OllamaHealthResult,
    OllamaTaskClassification,
    ProviderHealth,
)

logger = logging.getLogger(__name__)

OLLAMA_TAGS_PATH = "/api/tags"
OLLAMA_GENERATE_PATH = "/api/generate"
OLLAMA_CHAT_PATH = "/api/chat"


class OllamaProvider(BrainProvider):
    """SATURNIX Ollama provider for local/private execution.

    Supported local model aliases:

    - `gemma`
    - `minimax`
    - `qwen coder`
    - `deepseek coder`
    """

    def __init__(
        self,
        name: BrainName,
        model: str,
        settings: Settings,
        capabilities: set[Capability],
        enabled: bool,
    ) -> None:
        self.name = name
        self.settings = settings
        self.capabilities = capabilities
        super().__init__(model=model, enabled=enabled)

    @property
    def base_url(self) -> str:
        return self.settings.ollama_base_url.rstrip("/")

    @property
    def supported_models(self) -> dict[str, str]:
        return {
            "gemma": self.settings.ollama_gemma_model,
            "minimax": self.settings.ollama_minimax_model,
            "qwen coder": self.settings.ollama_qwen_coder_model,
            "deepseek coder": self.settings.ollama_deepseek_coder_model,
        }

    async def health(self) -> ProviderHealth:
        health = await self.health_check()
        return ProviderHealth(
            name=self.name,
            model=self.model,
            enabled=health.enabled,
            available=health.running,
            capabilities=self.capability_list,
            detail=health.detail,
        )

    async def health_check(self) -> OllamaHealthResult:
        if not self.enabled:
            return OllamaHealthResult(
                enabled=False,
                running=False,
                base_url=self.base_url,
                supported_models=self.supported_models,
                missing_supported_models=self.supported_models,
                detail="Ollama is disabled. Set SATURNIX_ENABLE_OLLAMA=true to enable it.",
            )
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(f"{self.base_url}{OLLAMA_TAGS_PATH}")
            if response.status_code >= 400:
                return OllamaHealthResult(
                    enabled=True,
                    running=False,
                    base_url=self.base_url,
                    supported_models=self.supported_models,
                    missing_supported_models=self.supported_models,
                    detail=f"Ollama health check failed: {response.status_code} {response.text}",
                )
            data = response.json()
            available_models = [
                item.get("name", "")
                for item in data.get("models", [])
                if item.get("name")
            ]
            missing = {
                alias: model
                for alias, model in self.supported_models.items()
                if not _model_available(model, available_models)
            }
            return OllamaHealthResult(
                enabled=True,
                running=True,
                base_url=self.base_url,
                available_models=available_models,
                supported_models=self.supported_models,
                missing_supported_models=missing,
                detail=None if not missing else "Ollama is running; some supported models are not pulled.",
            )
        except httpx.RequestError as exc:
            return OllamaHealthResult(
                enabled=True,
                running=False,
                base_url=self.base_url,
                supported_models=self.supported_models,
                missing_supported_models=self.supported_models,
                detail=f"Ollama is not reachable at {self.base_url}: {exc}",
            )
        except Exception as exc:  # pragma: no cover - defensive local adapter boundary
            logger.exception("Unexpected Ollama health check failure.")
            return OllamaHealthResult(
                enabled=True,
                running=False,
                base_url=self.base_url,
                supported_models=self.supported_models,
                missing_supported_models=self.supported_models,
                detail=str(exc),
            )

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        fallback_text: str | None = None,
    ) -> OllamaGenerationResult:
        selected_model = self.resolve_model(model or self.model)
        if not self.enabled:
            return _fallback_generation_result(
                model=selected_model,
                error="Ollama provider is disabled. Set SATURNIX_ENABLE_OLLAMA=true to enable it.",
                fallback_text=fallback_text,
            )
        payload = {
            "model": selected_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        try:
            async with httpx.AsyncClient(timeout=self.settings.ollama_request_timeout) as client:
                response = await client.post(f"{self.base_url}{OLLAMA_GENERATE_PATH}", json=payload)
        except httpx.RequestError as exc:
            return _fallback_generation_result(
                model=selected_model,
                error=f"Ollama is not reachable at {self.base_url}: {exc}",
                fallback_text=fallback_text,
            )
        if response.status_code >= 400:
            return _fallback_generation_result(
                model=selected_model,
                error=f"Ollama generate failed: {response.status_code} {response.text}",
                fallback_text=fallback_text,
            )
        data = response.json()
        return OllamaGenerationResult(
            ok=True,
            model=selected_model,
            output=data.get("response", ""),
            raw=data,
        )

    async def code_generate(
        self,
        prompt: str,
        model: str | None = None,
        language: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        fallback_text: str | None = None,
    ) -> OllamaGenerationResult:
        selected_model = self.resolve_model(model or self.settings.ollama_coding_model)
        language_hint = f"\nTarget language: {language}." if language else ""
        system = (
            "You are SATURNIX local coding brain. Produce concise, correct, testable code. "
            "Prefer clear function boundaries and include assumptions when needed."
        )
        return await self.generate(
            prompt=f"{prompt}{language_hint}",
            model=selected_model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            fallback_text=fallback_text,
        )

    async def summarize(
        self,
        text: str,
        model: str | None = "gemma",
        max_tokens: int | None = 512,
        fallback_text: str | None = None,
    ) -> OllamaGenerationResult:
        prompt = (
            "Summarize the following content for SATURNIX memory. "
            "Keep durable facts, decisions, risks, and next actions.\n\n"
            f"{text}"
        )
        return await self.generate(
            prompt=prompt,
            model=model,
            system="You are a local/private summarization model.",
            temperature=0.2,
            max_tokens=max_tokens,
            fallback_text=fallback_text,
        )

    def classify_task(self, task: str) -> OllamaTaskClassification:
        lowered = task.lower()
        if _contains_any(lowered, {"code", "debug", "function", "class", "api", "test", "refactor"}):
            task_type = "coding"
            local_model = self.resolve_model(self.settings.ollama_coding_model)
            output_format = "code"
        elif _contains_any(lowered, {"summarize", "summary", "notes", "memory"}):
            task_type = "summarization"
            local_model = self.resolve_model("gemma")
            output_format = "markdown"
        elif _contains_any(lowered, {"json", "schema", "classify", "label", "category"}):
            task_type = "classification"
            local_model = self.resolve_model("gemma")
            output_format = "json"
        else:
            task_type = "local_reasoning"
            local_model = self.resolve_model("gemma")
            output_format = "markdown"
        privacy_level = "local" if _contains_any(
            lowered,
            {"private", "local", "offline", "confidential", "sensitive"},
        ) else "standard"
        speed_priority = "high" if _contains_any(
            lowered,
            {"fast", "quick", "urgent", "low latency", "realtime", "real-time"},
        ) else "normal"
        context_size = "large" if len(task) > 4000 or _contains_any(
            lowered,
            {"large context", "long document", "many files", "full repository"},
        ) else "small"
        return OllamaTaskClassification(
            task_type=task_type,
            privacy_level=privacy_level,
            speed_priority=speed_priority,
            context_size=context_size,
            output_format=output_format,
            local_model=local_model,
            reason="Classified locally using deterministic SATURNIX Ollama routing heuristics.",
        )

    def resolve_model(self, model_or_alias: str) -> str:
        normalized = model_or_alias.strip().lower().replace("_", " ").replace("-", " ")
        aliases = {
            "gemma": self.settings.ollama_gemma_model,
            "gemma3": self.settings.ollama_gemma_model,
            "minimax": self.settings.ollama_minimax_model,
            "qwen coder": self.settings.ollama_qwen_coder_model,
            "qwen": self.settings.ollama_qwen_coder_model,
            "qwen2.5 coder": self.settings.ollama_qwen_coder_model,
            "qwen 2.5 coder": self.settings.ollama_qwen_coder_model,
            "deepseek coder": self.settings.ollama_deepseek_coder_model,
            "deepseek": self.settings.ollama_deepseek_coder_model,
            "deepseek coder v2": self.settings.ollama_deepseek_coder_model,
            self.settings.ollama_coding_model.lower().replace("-", " "): self.settings.ollama_coding_model,
        }
        return aliases.get(normalized, model_or_alias)

    async def complete(self, request: BrainRequest) -> BrainResponse:
        if not self.enabled:
            raise BrainProviderError("Ollama provider is disabled.")
        payload = {
            "model": self.model,
            "messages": [message.model_dump() for message in request.messages],
            "stream": False,
            "options": {"temperature": request.temperature},
        }
        if request.max_tokens:
            payload["options"]["num_predict"] = request.max_tokens
        try:
            async with httpx.AsyncClient(timeout=self.settings.ollama_request_timeout) as client:
                response = await client.post(f"{self.base_url}{OLLAMA_CHAT_PATH}", json=payload)
        except httpx.RequestError as exc:
            raise BrainProviderError(f"Ollama is unavailable at {self.base_url}: {exc}") from exc
        if response.status_code >= 400:
            raise BrainProviderError(f"Ollama request failed: {response.status_code} {response.text}")
        data = response.json()
        content = data.get("message", {}).get("content", "")
        if not content and data.get("response"):
            content = data["response"]
        return BrainResponse(provider=self.name, model=self.model, content=content, raw=data)


class SaturnixOllamaProvider(OllamaProvider):
    """Concrete SATURNIX local provider using the standard localhost Ollama daemon."""

    name = BrainName.ollama_gemma
    capabilities = {
        Capability.reasoning,
        Capability.coding,
        Capability.local_private,
        Capability.planning,
        Capability.verification,
    }

    def __init__(self, settings: Settings) -> None:
        super().__init__(
            name=BrainName.ollama_gemma,
            model=settings.ollama_gemma_model,
            settings=settings,
            enabled=True,
            capabilities=set(self.capabilities),
        )


def _fallback_generation_result(
    model: str,
    error: str,
    fallback_text: str | None,
) -> OllamaGenerationResult:
    logger.warning("Ollama fallback used for model %s: %s", model, error)
    return OllamaGenerationResult(
        ok=False,
        model=model,
        output=fallback_text or "",
        raw={},
        fallback_used=bool(fallback_text),
        error=error,
    )


def _model_available(model: str, available_models: list[str]) -> bool:
    wanted = model.lower()
    return any(
        available.lower() == wanted
        or available.lower().startswith(f"{wanted}:")
        or wanted.startswith(f"{available.lower()}:")
        for available in available_models
    )


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def build_ollama_gemma(settings: Settings) -> OllamaProvider:
    return OllamaProvider(
        name=BrainName.ollama_gemma,
        model=settings.ollama_gemma_model,
        settings=settings,
        enabled=settings.saturnix_enable_ollama,
        capabilities={
            Capability.reasoning,
            Capability.local_private,
            Capability.planning,
            Capability.verification,
        },
    )


def build_ollama_coding(settings: Settings) -> OllamaProvider:
    return OllamaProvider(
        name=BrainName.ollama_coding,
        model=settings.ollama_coding_model,
        settings=settings,
        enabled=settings.saturnix_enable_ollama,
        capabilities={
            Capability.coding,
            Capability.local_private,
            Capability.reasoning,
            Capability.verification,
        },
    )
