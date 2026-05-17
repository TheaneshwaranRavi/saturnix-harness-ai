from __future__ import annotations

import httpx

from saturnix_harness.brains.base import BrainProvider
from saturnix_harness.config import Settings
from saturnix_harness.exceptions import BrainProviderError
from saturnix_harness.schemas import BrainName, BrainRequest, BrainResponse, Capability


class ClaudeProvider(BrainProvider):
    name = BrainName.claude
    capabilities = {
        Capability.reasoning,
        Capability.long_context,
        Capability.document_understanding,
        Capability.planning,
        Capability.verification,
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        super().__init__(
            model=settings.claude_model,
            enabled=settings.has_secret(settings.anthropic_api_key),
        )

    async def complete(self, request: BrainRequest) -> BrainResponse:
        if not self.enabled or not self.settings.anthropic_api_key:
            raise BrainProviderError("Claude provider is not configured.")
        system_parts = [message.content for message in request.messages if message.role == "system"]
        messages = [
            {"role": message.role, "content": message.content}
            for message in request.messages
            if message.role in {"user", "assistant"}
        ]
        payload: dict = {
            "model": self.model,
            "max_tokens": request.max_tokens or 2048,
            "temperature": request.temperature,
            "messages": messages,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        headers = {
            "x-api-key": self.settings.anthropic_api_key.get_secret_value(),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
        if response.status_code >= 400:
            raise BrainProviderError(f"Claude request failed: {response.status_code} {response.text}")
        data = response.json()
        content_blocks = data.get("content", [])
        content = "\n".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")
        return BrainResponse(provider=self.name, model=self.model, content=content, raw=data)
