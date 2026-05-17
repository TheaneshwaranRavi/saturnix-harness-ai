from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from saturnix_harness.schemas import ToolResult, ToolSpec


class Tool(ABC):
    name: str
    description: str
    input_schema: dict[str, Any]

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
        )

    @abstractmethod
    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        raise NotImplementedError

