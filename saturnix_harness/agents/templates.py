from saturnix_harness.prompts import load_prompt
from saturnix_harness.schemas import AgentSpec, BrainName, Capability, IntentMap


def architect_agent(intent: IntentMap, preferred_brain: BrainName | None = None) -> AgentSpec:
    return AgentSpec(
        name="saturnix_architect",
        role="Agent Architecture Designer",
        mission="Translate goals into a modular agent architecture and execution strategy.",
        system_prompt=load_prompt("architect.md"),
        required_capabilities=[Capability.reasoning, Capability.planning, Capability.orchestration],
        preferred_brain=preferred_brain,
        tools=["echo", "current_time", "safe_calculator"],
        memory_namespace=f"agent:{intent.domain}",
    )


def coding_agent(intent: IntentMap, preferred_brain: BrainName | None = None) -> AgentSpec:
    return AgentSpec(
        name="saturnix_coding_engineer",
        role="Coding and Implementation Agent",
        mission="Create implementation plans, code patches, and integration steps.",
        system_prompt=load_prompt("coding_agent.md"),
        required_capabilities=[Capability.coding, Capability.reasoning],
        preferred_brain=preferred_brain,
        tools=["echo", "safe_calculator"],
        memory_namespace=f"agent:{intent.domain}",
    )


def verifier_agent(intent: IntentMap, preferred_brain: BrainName | None = None) -> AgentSpec:
    return AgentSpec(
        name="saturnix_verifier",
        role="Self-Verification Critic",
        mission="Check outputs against the original human intent and recommend improvements.",
        system_prompt=load_prompt("verifier.md"),
        required_capabilities=[Capability.reasoning, Capability.verification],
        preferred_brain=preferred_brain,
        tools=[],
        memory_namespace=f"agent:{intent.domain}",
    )
