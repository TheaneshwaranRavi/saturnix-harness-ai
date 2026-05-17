from saturnix_harness.brains.base import BrainProvider, messages_to_text
from saturnix_harness.schemas import BrainName, BrainRequest, BrainResponse, Capability


class MockProvider(BrainProvider):
    """Offline provider used for tests, demos, and first-run local development."""

    name = BrainName.mock
    capabilities = {
        Capability.reasoning,
        Capability.coding,
        Capability.planning,
        Capability.orchestration,
        Capability.structured_output,
        Capability.function_calling,
        Capability.local_private,
        Capability.verification,
    }

    async def complete(self, request: BrainRequest) -> BrainResponse:
        text = messages_to_text(request)
        system_text = "\n".join(
            message.content for message in request.messages if message.role == "system"
        ).lower()
        last_user = next(
            (message.content for message in reversed(request.messages) if message.role == "user"),
            text,
        )
        if request.response_schema:
            content = '{"status":"ok","provider":"mock","note":"schema-aware mock response"}'
        elif "improve the output" in system_text:
            content = (
                "SATURNIX improved output:\n"
                "- Actionable response: the requested system should be split into intent, "
                "architecture, routing, execution, verification, and memory modules.\n"
                "- Modular architecture: use independent agents with explicit capabilities, "
                "provider preferences, tools, and memory namespaces.\n"
                "- Structured output: expose the final plan through API and CLI contracts so "
                "future real providers can replace this mock response without changing callers."
            )
        elif "verification agent" in system_text or "verify the output" in system_text:
            content = "Verification passed: output is coherent, non-empty, and aligned with the goal."
        else:
            content = (
                "SATURNIX mock brain response:\n"
                f"- Interpreted request: {last_user.strip()[:700]}\n"
                "- Actionable response: define the agents, choose provider capabilities, run the "
                "workflow, and verify the final result.\n"
                "- Modular architecture: keep orchestration, routing, tools, memory, voice, and "
                "verification behind reusable interfaces.\n"
                "- Structured output: return traces, provider decisions, verification score, and "
                "memory records through stable Pydantic models."
            )
        return BrainResponse(provider=self.name, model=self.model, content=content)
