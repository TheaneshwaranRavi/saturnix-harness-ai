from __future__ import annotations

import httpx

from saturnix_harness.brains.base import BrainProvider
from saturnix_harness.config import Settings
from saturnix_harness.exceptions import BrainProviderError
from saturnix_harness.schemas import BrainName, BrainRequest, BrainResponse, Capability


class GroqProvider(BrainProvider):
    name = BrainName.groq
    capabilities = {
        Capability.voice,
        Capability.realtime_speech,
        Capability.reasoning,
        Capability.structured_output,
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        super().__init__(
            model=settings.groq_chat_model,
            enabled=settings.has_secret(settings.groq_api_key),
        )

    async def complete(self, request: BrainRequest) -> BrainResponse:
        if not self.enabled or not self.settings.groq_api_key:
            raise BrainProviderError("Groq provider is not configured.")
        payload = {
            "model": self.model,
            "messages": [message.model_dump() for message in request.messages],
            "temperature": request.temperature,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
            )
        if response.status_code >= 400:
            raise BrainProviderError(f"Groq request failed: {response.status_code} {response.text}")
        data = response.json()
        content = data["choices"][0]["message"].get("content", "")
        return BrainResponse(provider=self.name, model=self.model, content=content, raw=data)
