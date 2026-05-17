from saturnix_harness.schemas import AgentSpec, BrainName, Capability


DOCUMENT_ANALYST = AgentSpec(
    name="document_analyst",
    role="Long-context document analyst",
    mission="Read large documents and extract risk, obligations, and action items.",
    system_prompt=(
        "You are a careful document-understanding agent. Extract important facts, "
        "cite the relevant section names when available, and identify uncertainty."
    ),
    required_capabilities=[Capability.long_context, Capability.document_understanding, Capability.reasoning],
    preferred_brain=BrainName.claude,
    tools=["echo"],
    memory_namespace="examples:documents",
)


JSON_FUNCTION_AGENT = AgentSpec(
    name="json_function_agent",
    role="Structured-output and function-calling agent",
    mission="Return strict JSON payloads and choose tool calls when useful.",
    system_prompt=(
        "You are a structured-output agent. Prefer valid JSON and explicit tool arguments."
    ),
    required_capabilities=[Capability.structured_output, Capability.function_calling],
    preferred_brain=BrainName.gemini,
    tools=["current_time", "safe_calculator"],
    memory_namespace="examples:structured",
)


LOCAL_CODING_AGENT = AgentSpec(
    name="local_coding_agent",
    role="Private local coding assistant",
    mission="Draft and review small code units using local Ollama models.",
    system_prompt="You are a local coding agent. Keep code concise, testable, and private.",
    required_capabilities=[Capability.coding, Capability.local_private],
    preferred_brain=BrainName.ollama_coding,
    tools=["safe_calculator"],
    memory_namespace="examples:local_code",
)

