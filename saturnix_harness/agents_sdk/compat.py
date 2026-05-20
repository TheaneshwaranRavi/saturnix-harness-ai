from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentsSDKRuntime:
    available: bool
    error: str | None = None
    Agent: Any = None
    Runner: Any = None
    SQLiteSession: Any = None
    function_tool: Any = None
    input_guardrail: Any = None
    GuardrailFunctionOutput: Any = None
    trace: Any = None


def load_agents_sdk() -> AgentsSDKRuntime:
    try:
        from agents import (  # type: ignore
            Agent,
            GuardrailFunctionOutput,
            Runner,
            SQLiteSession,
            function_tool,
            input_guardrail,
            trace,
        )
    except Exception as exc:  # pragma: no cover - depends on optional SDK import health
        return AgentsSDKRuntime(
            available=False,
            error=f"{type(exc).__name__}: {exc}",
            function_tool=_identity_decorator,
            input_guardrail=_identity_decorator,
            trace=_noop_trace,
        )
    return AgentsSDKRuntime(
        available=True,
        Agent=Agent,
        Runner=Runner,
        SQLiteSession=SQLiteSession,
        function_tool=function_tool,
        input_guardrail=input_guardrail,
        GuardrailFunctionOutput=GuardrailFunctionOutput,
        trace=trace,
    )


def _identity_decorator(func=None, **_kwargs):
    if func is None:
        return lambda wrapped: wrapped
    return func


@contextmanager
def _noop_trace(*_args, **_kwargs):
    yield None
