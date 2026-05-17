from __future__ import annotations

import ast
import operator
from datetime import datetime, timezone
from typing import Any

from saturnix_harness.schemas import ToolResult
from saturnix_harness.tools.base import Tool


class EchoTool(Tool):
    name = "echo"
    description = "Return the supplied text. Useful for wiring tests and simple workflows."
    input_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(name=self.name, ok=True, output=arguments.get("text", ""))


class CurrentTimeTool(Tool):
    name = "current_time"
    description = "Return the current UTC timestamp."
    input_schema = {"type": "object", "properties": {}}

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(name=self.name, ok=True, output=datetime.now(timezone.utc).isoformat())


class SafeCalculatorTool(Tool):
    name = "safe_calculator"
    description = "Evaluate a basic arithmetic expression using a safe AST evaluator."
    input_schema = {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    }

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        expression = str(arguments.get("expression", ""))
        try:
            output = _safe_eval(expression)
        except Exception as exc:
            return ToolResult(name=self.name, ok=False, error=str(exc))
        return ToolResult(name=self.name, ok=True, output=output)


_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _safe_eval(expression: str) -> float | int:
    node = ast.parse(expression, mode="eval")
    return _eval_node(node.body)


def _eval_node(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Only basic arithmetic expressions are allowed.")


def built_in_tools() -> list[Tool]:
    return [EchoTool(), CurrentTimeTool(), SafeCalculatorTool()]

