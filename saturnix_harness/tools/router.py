from __future__ import annotations

from saturnix_harness.exceptions import ToolExecutionError
from saturnix_harness.schemas import ToolCall, ToolResult, ToolSpec
from saturnix_harness.tools.base import Tool
from saturnix_harness.tools.builtin import built_in_tools


class ToolRouter:
    """Tool router with a registry-based extension point."""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self.tools: dict[str, Tool] = {}
        for tool in tools or built_in_tools():
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def specs(self) -> list[ToolSpec]:
        return [tool.spec() for tool in self.tools.values()]

    async def execute(self, call: ToolCall) -> ToolResult:
        tool = self.tools.get(call.name)
        if not tool:
            raise ToolExecutionError(f"Unknown tool: {call.name}")
        result = await tool.run(call.arguments)
        if not result.ok:
            raise ToolExecutionError(result.error or f"Tool failed: {call.name}")
        return result

