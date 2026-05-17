from __future__ import annotations

import time
from abc import ABC, abstractmethod

from saturnix_harness.schemas import BrainName, BrainRequest, BrainResponse, Capability, ProviderHealth


class BrainProvider(ABC):
    """Base contract implemented by every reasoning/model backend."""

    name: BrainName
    model: str
    capabilities: set[Capability]
    enabled: bool = True

    def __init__(self, model: str, enabled: bool = True) -> None:
        self.model = model
        self.enabled = enabled

    @property
    def capability_list(self) -> list[Capability]:
        return sorted(self.capabilities, key=lambda value: value.value)

    async def health(self) -> ProviderHealth:
        return ProviderHealth(
            name=self.name,
            model=self.model,
            enabled=self.enabled,
            available=self.enabled,
            capabilities=self.capability_list,
            detail=None if self.enabled else "provider is disabled or missing credentials",
        )

    @abstractmethod
    async def complete(self, request: BrainRequest) -> BrainResponse:
        raise NotImplementedError

    async def timed_complete(self, request: BrainRequest) -> BrainResponse:
        start = time.perf_counter()
        response = await self.complete(request)
        response.latency_ms = int((time.perf_counter() - start) * 1000)
        return response

    def can_satisfy(self, capabilities: list[Capability]) -> bool:
        return set(capabilities).issubset(self.capabilities)


def messages_to_text(request: BrainRequest) -> str:
    return "\n".join(f"{message.role.upper()}: {message.content}" for message in request.messages)

