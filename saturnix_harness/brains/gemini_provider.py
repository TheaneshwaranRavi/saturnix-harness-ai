from __future__ import annotations

import httpx

from saturnix_harness.brains.base import BrainProvider
from saturnix_harness.config import Settings
from saturnix_harness.exceptions import BrainProviderError
from saturnix_harness.schemas import BrainName, BrainRequest, BrainResponse, Capability


class GeminiProvider(BrainProvider):
    name = BrainName.gemini
    capabilities = {
        Capability.reasoning,
        Capability.structured_output,
        Capability.function_calling,
        Capability.planning,
        Capability.verification,
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        super().__init__(
            model=settings.gemini_model,
            enabled=settings.has_secret(settings.google_api_key),
        )

    async def complete(self, request: BrainRequest) -> BrainResponse:
        if not self.enabled or not self.settings.google_api_key:
            raise BrainProviderError("Gemini provider is not configured.")
        contents = []
        system_instruction = None
        for message in request.messages:
            if message.role == "system":
                system_instruction = {"parts": [{"text": message.content}]}
            else:
                role = "model" if message.role == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": message.content}]})
        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        if request.response_schema:
            payload["generationConfig"]["responseMimeType"] = "application/json"
            payload["generationConfig"]["responseSchema"] = request.response_schema
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                params={"key": self.settings.google_api_key.get_secret_value()},
                json=payload,
            )
        if response.status_code >= 400:
            raise BrainProviderError(f"Gemini request failed: {response.status_code} {response.text}")
        data = response.json()
        candidates = data.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        content = "\n".join(part.get("text", "") for part in parts)
        return BrainResponse(provider=self.name, model=self.model, content=content, raw=data)
