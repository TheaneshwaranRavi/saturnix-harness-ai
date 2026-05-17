from __future__ import annotations

from saturnix_harness.schemas import AgentSpec, Capability, IntentMap, WorkflowPlan, WorkflowStep


class NavigationWorkflowBuilder:
    """N: Navigation Workflow."""

    def build(self, intent: IntentMap, agents: list[AgentSpec], input_text: str | None = None) -> WorkflowPlan:
        architect = next(agent for agent in agents if agent.name == "saturnix_architect")
        coding = next((agent for agent in agents if agent.name == "saturnix_coding_engineer"), architect)

        context = input_text or "No additional input supplied."
        architecture_prompt = (
            f"Goal: {intent.original_goal}\n"
            f"Intent summary: {intent.summary}\n"
            f"Expected outputs: {', '.join(intent.expected_outputs)}\n"
            f"Constraints: {', '.join(intent.constraints) or 'none'}\n\n"
            "Design the agent system or solution architecture needed to satisfy this goal."
        )
        execution_prompt = (
            f"Using the architecture and context below, produce the concrete output.\n\n"
            f"Original goal:\n{intent.original_goal}\n\n"
            f"Input context:\n{context}"
        )

        architecture_step = WorkflowStep(
            name="Map Architecture",
            agent_name=architect.name,
            action="brain",
            prompt=architecture_prompt,
            required_capabilities=[Capability.planning, Capability.reasoning],
        )
        execution_step = WorkflowStep(
            name="Execute Construction",
            agent_name=coding.name,
            action="brain",
            prompt=execution_prompt,
            required_capabilities=list(intent.required_capabilities),
            depends_on=[architecture_step.id],
        )
        steps = [
            architecture_step,
            execution_step,
        ]
        return WorkflowPlan(goal=intent.original_goal, steps=steps, agents=agents)
