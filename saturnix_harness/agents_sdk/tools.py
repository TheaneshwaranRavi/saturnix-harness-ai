from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from saturnix_harness.agents_sdk.compat import load_agents_sdk
from saturnix_harness.config import Settings
from saturnix_harness.core.security_sentinel import SecuritySentinel
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.schemas import (
    MemoryType,
    SaveMemoryRequest,
    SearchMemoryRequest,
    SaturnixToolUsageRecord,
    SecurityScanRequest,
)


@dataclass(frozen=True)
class SaturnixSDKTool:
    name: str
    description: str
    sdk_tool: Any


class SaturnixSDKToolFactory:
    """Reusable tools exposed to OpenAI Agents SDK agents."""

    def __init__(
        self,
        *,
        settings: Settings,
        memory: MemoryManager,
        security_sentinel: SecuritySentinel,
    ) -> None:
        self.settings = settings
        self.memory = memory
        self.security_sentinel = security_sentinel
        self.usage: list[SaturnixToolUsageRecord] = []
        self.sdk = load_agents_sdk()

    def build_for_agent(self, tool_names: list[str]) -> list[Any]:
        tools = self.registry()
        return [tools[name].sdk_tool for name in tool_names if name in tools]

    def registry(self) -> dict[str, SaturnixSDKTool]:
        return {
            "web_search_tool": self._tool(
                "web_search_tool",
                "Return a web-search routing plan. Live browsing is mediated by SATURNIX.",
                self._web_search_tool,
            ),
            "memory_search_tool": self._tool(
                "memory_search_tool",
                "Search SATURNIX local memory.",
                self._memory_search_tool,
            ),
            "file_access_tool": self._tool(
                "file_access_tool",
                "Validate a file path against allowed storage roots.",
                self._file_access_tool,
            ),
            "code_execution_tool": self._tool(
                "code_execution_tool",
                "Prepare a sandboxed code execution plan.",
                self._code_execution_tool,
            ),
            "workflow_tool": self._tool(
                "workflow_tool",
                "Create a dependency-aware workflow outline.",
                self._workflow_tool,
            ),
            "security_scan_tool": self._tool(
                "security_scan_tool",
                "Scan input for SATURNIX security risks.",
                self._security_scan_tool,
            ),
            "voice_transcription_tool": self._tool(
                "voice_transcription_tool",
                "Route voice transcription through the Groq voice layer.",
                self._voice_transcription_tool,
            ),
            "edge_node_tool": self._tool(
                "edge_node_tool",
                "Prepare a signed Raspberry Pi edge-node command plan.",
                self._edge_node_tool,
            ),
        }

    def _tool(self, name: str, description: str, func: Callable[..., str]) -> SaturnixSDKTool:
        if self.sdk.available:
            return SaturnixSDKTool(name=name, description=description, sdk_tool=self.sdk.function_tool(func))
        return SaturnixSDKTool(name=name, description=description, sdk_tool=func)

    def _record(self, tool_name: str, ok: bool, detail: str, started: float) -> str:
        self.usage.append(
            SaturnixToolUsageRecord(
                tool_name=tool_name,
                ok=ok,
                detail=detail,
                latency_ms=int((perf_counter() - started) * 1000),
            )
        )
        return detail

    def _web_search_tool(self, query: str) -> str:
        started = perf_counter()
        return self._record(
            "web_search_tool",
            True,
            f"Web search requested for '{query}'. SATURNIX will route browsing through approved tools.",
            started,
        )

    def _memory_search_tool(self, query: str, namespace: str = "default", limit: int = 5) -> str:
        started = perf_counter()
        records = self.memory.search_memory(
            SearchMemoryRequest(query=query, namespace=namespace, limit=limit)
        )
        detail = "; ".join((record.title or record.content[:80]) for record in records)
        return self._record(
            "memory_search_tool",
            True,
            detail or "No matching SATURNIX memory records found.",
            started,
        )

    def _file_access_tool(self, path: str) -> str:
        started = perf_counter()
        allowed_roots = [
            Path(root).resolve()
            for root in self.settings.saturnix_allowed_storage_roots.split(",")
            if root.strip()
        ]
        candidate = Path(path).expanduser().resolve()
        ok = any(candidate == root or root in candidate.parents for root in allowed_roots)
        detail = (
            f"Allowed file access path: {candidate}"
            if ok
            else f"Blocked file path outside SATURNIX storage roots: {candidate}"
        )
        return self._record("file_access_tool", ok, detail, started)

    def _code_execution_tool(self, code: str, language: str = "python") -> str:
        started = perf_counter()
        scan = self.security_sentinel.scan(SecurityScanRequest(code=code, actions=[language]))
        if scan.blocked_actions:
            return self._record(
                "code_execution_tool",
                False,
                f"Code execution blocked: {scan.blocked_actions}",
                started,
            )
        return self._record(
            "code_execution_tool",
            True,
            f"Sandbox execution plan prepared for {language}; execution requires approval.",
            started,
        )

    def _workflow_tool(self, goal: str) -> str:
        started = perf_counter()
        return self._record(
            "workflow_tool",
            True,
            f"Workflow plan: intent -> route brain -> assign agents -> execute -> verify -> save memory for '{goal}'.",
            started,
        )

    def _security_scan_tool(self, text: str) -> str:
        started = perf_counter()
        scan = self.security_sentinel.scan(SecurityScanRequest(prompt=text))
        return self._record(
            "security_scan_tool",
            not bool(scan.blocked_actions),
            scan.model_dump_json(),
            started,
        )

    def _voice_transcription_tool(self, filename: str) -> str:
        started = perf_counter()
        return self._record(
            "voice_transcription_tool",
            True,
            f"Voice file '{filename}' queued for Groq transcription through Voice Engine.",
            started,
        )

    def _edge_node_tool(self, command: str) -> str:
        started = perf_counter()
        scan = self.security_sentinel.scan(SecurityScanRequest(actions=[command]))
        ok = not bool(scan.blocked_actions)
        detail = (
            f"Signed edge-node command plan prepared: {command}"
            if ok
            else f"Edge command blocked: {scan.blocked_actions}"
        )
        return self._record("edge_node_tool", ok, detail, started)

    def save_trace_note(self, content: str, agent_name: str) -> None:
        self.memory.save_memory(
            SaveMemoryRequest(
                content=content,
                memory_type=MemoryType.agent_execution_logs,
                namespace=self.settings.saturnix_agents_trace_namespace,
                kind="sdk_tool_trace",
                title=f"Tool trace: {agent_name}",
                tags=["agents_sdk", "tool_usage"],
                source="agents_sdk",
            )
        )
