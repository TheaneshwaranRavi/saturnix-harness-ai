from __future__ import annotations

from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.schemas import AgentSpec, BrainMessage, BrainRequest, BrainResponse
from saturnix_harness.tools.router import ToolRouter


class AgentRuntime:
    """Executable agent bound to a brain router, tools, and memory namespace."""

    def __init__(
        self,
        spec: AgentSpec,
        brain_router: BrainRouter,
        tool_router: ToolRouter,
        memory: MemoryManager,
    ) -> None:
        self.spec = spec
        self.brain_router = brain_router
        self.tool_router = tool_router
        self.memory = memory

    async def run(self, prompt: str, context: str | None = None) -> BrainResponse:
        memory_hits = self.memory.recall(prompt, namespace=self.spec.memory_namespace, limit=3)
        memory_context = "\n".join(f"- {record.content}" for record in memory_hits)
        system_prompt = self.spec.system_prompt
        if self.spec.tools:
            system_prompt += "\n\nAvailable tools: " + ", ".join(self.spec.tools)
        if memory_context:
            system_prompt += f"\n\nRelevant memory:\n{memory_context}"
        messages = [BrainMessage(role="system", content=system_prompt)]
        if context:
            messages.append(BrainMessage(role="user", content=f"Context:\n{context}"))
        messages.append(BrainMessage(role="user", content=prompt))
        response = await self.brain_router.complete(
            BrainRequest(
                messages=messages,
                required_capabilities=self.spec.required_capabilities,
                preferred_brain=self.spec.preferred_brain,
            )
        )
        self.memory.remember(
            content=f"Agent {self.spec.name} handled: {prompt[:300]}",
            namespace=self.spec.memory_namespace,
            kind="agent_trace",
            metadata={"provider": response.provider.value, "model": response.model},
        )
        return response

