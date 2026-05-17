from __future__ import annotations

import httpx

from saturnix_harness.brains.base import BrainProvider
from saturnix_harness.config import Settings
from saturnix_harness.exceptions import BrainProviderError
from saturnix_harness.schemas import BrainName, BrainRequest, BrainResponse, Capability


class OpenAIProvider(BrainProvider):
    name = BrainName.openai
    capabilities = {
        Capability.reasoning,
        Capability.coding,
        Capability.planning,
        Capability.orchestration,
        Capability.structured_output,
        Capability.function_calling,
        Capability.verification,
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        super().__init__(
            model=settings.openai_model,
            enabled=settings.has_secret(settings.openai_api_key),
        )

    async def complete(self, request: BrainRequest) -> BrainResponse:
        if not self.enabled or not self.settings.openai_api_key:
            raise BrainProviderError("OpenAI provider is not configured.")
        payload: dict = {
            "model": self.model,
            "messages": [message.model_dump() for message in request.messages],
            "temperature": request.temperature,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.response_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.metadata.get("schema_name", "saturnix_schema"),
                    "schema": request.response_schema,
                },
            }
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
        if response.status_code >= 400:
            raise BrainProviderError(f"OpenAI request failed: {response.status_code} {response.text}")
        data = response.json()
        content = data["choices"][0]["message"].get("content", "")
        return BrainResponse(
            provider=self.name,
            model=self.model,
            content=content,
            raw=data,
            usage=data.get("usage", {}),
        )
