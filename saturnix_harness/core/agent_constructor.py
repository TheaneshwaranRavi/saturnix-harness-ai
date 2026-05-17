from __future__ import annotations

import json

from saturnix_harness.agents.base import AgentRuntime
from saturnix_harness.agents.blueprints import default_agent_blueprints
from saturnix_harness.agents.templates import architect_agent, coding_agent, verifier_agent
from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.schemas import (
    AgentFailureHandling,
    AgentInputDefinition,
    AgentMemoryRules,
    AgentSpec,
    AgentValidationRule,
    AgentWorkflowStepDefinition,
    AutonomousAgentConstructionRequest,
    AutonomousAgentConstructionResult,
    AutonomousAgentDefinition,
    BrainName,
    BrainRouteRequest,
    Capability,
    ConstructAgentRequest,
    DynamicAgentRequest,
    IntentMap,
    MemoryType,
    SaveMemoryRequest,
    SaturnixAgentBlueprint,
    SearchMemoryRequest,
)
from saturnix_harness.tools.router import ToolRouter


class AgentConstructor:
    """A: Agent Architecture Design.

    The constructor produces two useful artifacts:

    - `SaturnixAgentBlueprint`: rich production design for a specialized agent.
    - `AgentSpec`: lightweight executable runtime spec used by the execution engine.
    """

    def __init__(
        self,
        brain_router: BrainRouter,
        tool_router: ToolRouter,
        memory: MemoryManager,
    ) -> None:
        self.brain_router = brain_router
        self.tool_router = tool_router
        self.memory = memory
        self.default_blueprints = default_agent_blueprints()

    def construct_for_request(self, request: ConstructAgentRequest) -> AgentSpec:
        name = request.requested_name or "saturnix_custom_agent"
        role = "Custom SATURNIX Agent"
        mission = f"Satisfy goal: {request.goal}"
        system_prompt = (
            "You are a custom SATURNIX-HARNESS agent. Convert human intent into clear, "
            "verified work. Use routed tools and memory when appropriate."
        )
        return AgentSpec(
            name=name,
            role=role,
            mission=mission,
            system_prompt=system_prompt,
            required_capabilities=request.required_capabilities or [Capability.reasoning],
            preferred_brain=request.preferred_brain,
            tools=request.tools,
            memory_namespace=f"agent:{name}",
            metadata={"local_only": request.local_only},
        )

    def list_default_agents(self) -> list[SaturnixAgentBlueprint]:
        return list(self.default_blueprints.values())

    def get_default_agent(self, key_or_name: str) -> SaturnixAgentBlueprint:
        normalized = _normalize_agent_key(key_or_name)
        if normalized in self.default_blueprints:
            return self.default_blueprints[normalized]
        for blueprint in self.default_blueprints.values():
            if _normalize_agent_key(blueprint.agent_name) == normalized:
                return blueprint
        raise KeyError(f"Unknown default SATURNIX agent: {key_or_name}")

    def construct_blueprint(self, request: DynamicAgentRequest) -> SaturnixAgentBlueprint:
        """Create a specialized agent dynamically from task metadata."""

        purpose = request.purpose or request.task
        route = self.brain_router.route_task(
            BrainRouteRequest(
                task=request.task,
                task_type=request.task_type,
                privacy_level=request.privacy_level,
                speed_priority=request.speed_priority,
                context_size=request.context_size,
                output_format=request.output_format,
            )
        )
        agent_name = request.agent_name or _name_from_task(request.task, request.task_type)
        inputs = request.inputs or _default_inputs_for_task(request.task_type)
        tools = request.tools or _default_tools_for_task(request.task_type, route.selected_brain)
        validation_rules = request.validation_rules or _default_validation_rules(
            request.output_format,
            request.privacy_level,
            request.task_type,
        )
        namespace = request.memory_namespace or f"agent:{_normalize_agent_key(agent_name)}"
        return SaturnixAgentBlueprint(
            agent_name=agent_name,
            purpose=purpose,
            best_brain=route.selected_brain,
            inputs=inputs,
            tools=tools,
            workflow_steps=_default_workflow_steps(request.task_type, request.task),
            output_format=request.output_format,
            validation_rules=validation_rules,
            memory_rules=AgentMemoryRules(
                namespace=namespace,
                recall_policy=(
                    "retrieve relevant prior task summaries, user preferences, and durable facts"
                ),
                write_policy="store final outputs, validation results, and reusable decisions",
            ),
            failure_handling=AgentFailureHandling(
                fallback_brain=route.fallback_brain,
                retry_strategy=(
                    "retry once with clarified inputs, then reduce task scope and use fallback "
                    "brain"
                ),
                escalation_policy=(
                    "return structured failure details including missing inputs, failed step, "
                    "fallback attempted, and recommended human action"
                ),
            ),
        )

    def construct_autonomous(
        self,
        request: AutonomousAgentConstructionRequest,
    ) -> AutonomousAgentConstructionResult:
        """Create or reuse specialized agents based on task needs.

        The autonomous constructor is intentionally conservative: it reuses
        default SATURNIX agents first, checks memory for previously generated
        agents, and only creates a new blueprint when a specialization gap is
        real enough to justify another modular agent.
        """

        required_expertise = _required_expertise(request)
        task_complexity = _task_complexity(request, required_expertise)
        required_tools = _required_tools(request, required_expertise)
        security_requirements = _security_requirements(request, required_expertise)
        memory_needs = _memory_needs(request, required_expertise)
        execution_cost = _execution_cost(request, required_expertise, task_complexity)

        reused_agents: list[AutonomousAgentDefinition] = []
        created_agents: list[AutonomousAgentDefinition] = []
        duplicate_agents_avoided: list[str] = []
        saved_ids: list[str] = []
        seen_agents: set[str] = set()

        for expertise in required_expertise:
            if len(reused_agents) + len(created_agents) >= request.max_agents:
                duplicate_agents_avoided.append(
                    f"Skipped {expertise} specialization because max_agents was reached."
                )
                continue

            default_key = _DEFAULT_AGENT_BY_EXPERTISE.get(expertise)
            if default_key:
                definition = _definition_from_blueprint(self.default_blueprints[default_key])
                if _add_unique_agent(definition, reused_agents, seen_agents):
                    continue
                duplicate_agents_avoided.append(definition.agent_name)
                continue

            if not request.allow_new_agents:
                duplicate_agents_avoided.append(
                    f"Skipped new {expertise} agent because allow_new_agents is false."
                )
                continue

            agent_name = _agent_name_for_expertise(expertise)
            existing = self._load_autonomous_agent(agent_name)
            if existing:
                if _add_unique_agent(existing, reused_agents, seen_agents):
                    duplicate_agents_avoided.append(agent_name)
                continue

            definition = _build_autonomous_definition(
                request=request,
                expertise=expertise,
                required_tools=required_tools,
                security_requirements=security_requirements,
                memory_needs=memory_needs,
                route=self.brain_router.route_task(
                    BrainRouteRequest(
                        task=request.task,
                        task_type=expertise.replace("_", " "),
                        privacy_level=request.privacy_level,
                        speed_priority=request.speed_priority,
                        context_size=request.context_size,
                        output_format=request.output_format,
                    )
                ),
            )
            if not _add_unique_agent(definition, created_agents, seen_agents):
                duplicate_agents_avoided.append(definition.agent_name)
                continue
            saved_ids.append(self._save_autonomous_agent(definition, request, task_complexity))

        if not reused_agents and not created_agents:
            fallback = _definition_from_blueprint(self.default_blueprints["research_agent"])
            _add_unique_agent(fallback, reused_agents, seen_agents)

        all_agents = [*reused_agents, *created_agents]
        return AutonomousAgentConstructionResult(
            task_complexity=task_complexity,
            required_expertise=required_expertise,
            required_tools=required_tools,
            security_requirements=security_requirements,
            execution_cost=execution_cost,
            memory_needs=memory_needs,
            reused_agents=reused_agents,
            created_agents=created_agents,
            duplicate_agents_avoided=duplicate_agents_avoided,
            coordination_workflow=_coordination_workflow(all_agents),
            scalability_notes=_scalability_notes(created_agents, reused_agents),
            memory_saved={
                "namespace": "saturnix:agents",
                "created_agent_ids": saved_ids,
                "created_count": len(created_agents),
                "reused_count": len(reused_agents),
            },
        )

    def _load_autonomous_agent(self, agent_name: str) -> AutonomousAgentDefinition | None:
        records = self.memory.search_memory(
            SearchMemoryRequest(
                query=agent_name,
                namespace="saturnix:agents",
                memory_type=MemoryType.project_history,
                tags=["autonomous_agent"],
                limit=10,
                include_vector=False,
            )
        )
        normalized = _normalize_agent_key(agent_name)
        for record in records:
            data = record.metadata.get("agent_definition")
            if not data:
                continue
            definition = AutonomousAgentDefinition.model_validate(data)
            if _normalize_agent_key(definition.agent_name) == normalized:
                return definition
        return None

    def _save_autonomous_agent(
        self,
        definition: AutonomousAgentDefinition,
        request: AutonomousAgentConstructionRequest,
        task_complexity: str,
    ) -> str:
        record = self.memory.save_memory(
            SaveMemoryRequest(
                content=json.dumps(definition.model_dump(mode="json"), indent=2, sort_keys=True),
                memory_type=MemoryType.project_history,
                namespace="saturnix:agents",
                kind="dynamic_agent_blueprint",
                title=definition.agent_name,
                tags=["autonomous_agent", _normalize_agent_key(definition.agent_name)],
                metadata={
                    "task": request.task,
                    "task_type": request.task_type,
                    "task_complexity": task_complexity,
                    "agent_definition": definition.model_dump(mode="json"),
                },
                source="autonomous_agent_constructor",
            )
        )
        return record.id

    def construct_for_task(self, request: DynamicAgentRequest) -> AgentSpec:
        return self.to_agent_spec(self.construct_blueprint(request))

    def to_agent_spec(self, blueprint: SaturnixAgentBlueprint) -> AgentSpec:
        return AgentSpec(
            name=_normalize_agent_key(blueprint.agent_name),
            role=blueprint.agent_name,
            mission=blueprint.purpose,
            system_prompt=_system_prompt_from_blueprint(blueprint),
            required_capabilities=_capabilities_for_brain(blueprint.best_brain),
            preferred_brain=_preferred_brain_for_name(blueprint.best_brain),
            tools=blueprint.tools,
            memory_namespace=blueprint.memory_rules.namespace,
            metadata={
                "output_format": blueprint.output_format,
                "validation_rules": [rule.model_dump() for rule in blueprint.validation_rules],
                "failure_handling": blueprint.failure_handling.model_dump(),
            },
        )

    def construct_for_intent(self, intent: IntentMap, preferred_brain=None) -> list[AgentSpec]:
        agents = [architect_agent(intent, preferred_brain=preferred_brain)]
        if Capability.coding in intent.required_capabilities:
            agents.append(coding_agent(intent, preferred_brain=preferred_brain))
        agents.append(verifier_agent(intent, preferred_brain=preferred_brain))
        return agents

    def runtime(self, spec: AgentSpec) -> AgentRuntime:
        return AgentRuntime(
            spec=spec,
            brain_router=self.brain_router,
            tool_router=self.tool_router,
            memory=self.memory,
        )

    def runtime_map(self, specs: list[AgentSpec]) -> dict[str, AgentRuntime]:
        return {spec.name: self.runtime(spec) for spec in specs}


_EXPERTISE_KEYWORDS: dict[str, set[str]] = {
    "research": {
        "research",
        "source",
        "sources",
        "compare",
        "synthesize",
        "deep analysis",
        "analysis",
    },
    "coding": {
        "code",
        "coding",
        "implement",
        "debug",
        "refactor",
        "test",
        "api",
        "backend",
        "frontend",
    },
    "security": {
        "security",
        "secure",
        "threat",
        "risk",
        "privacy",
        "secret",
        "auth",
        "permission",
        "vulnerability",
    },
    "automation": {
        "automation",
        "workflow",
        "webhook",
        "n8n",
        "schedule",
        "function",
        "tool call",
        "integration",
    },
    "voice": {"voice", "speech", "audio", "transcription", "tts", "stt", "spoken"},
    "memory": {"memory", "recall", "remember", "store", "vector", "preference"},
    "verification": {"verify", "verification", "validate", "audit", "check", "quality"},
    "data_analysis": {"data", "csv", "sql", "analytics", "metrics", "dashboard", "report"},
    "compliance": {"compliance", "policy", "gdpr", "hipaa", "regulation", "legal"},
    "edge_deployment": {
        "raspberry pi",
        "edge",
        "device",
        "offline",
        "homelab",
        "local node",
    },
    "job_application": {"resume", "cover letter", "job", "application", "ats", "linkedin"},
    "semiconductor": {
        "semiconductor",
        "chip",
        "fab",
        "wafer",
        "node",
        "gpu",
        "asic",
        "foundry",
    },
}


_DEFAULT_AGENT_BY_EXPERTISE = {
    "research": "research_agent",
    "coding": "coding_agent",
    "automation": "automation_agent",
    "voice": "voice_agent",
    "memory": "memory_agent",
    "verification": "verification_agent",
    "job_application": "job_application_agent",
    "semiconductor": "semiconductor_agent",
}


_TOOLS_BY_EXPERTISE = {
    "research": ["memory_search", "document_parser", "web_search_optional"],
    "coding": ["code_search", "test_runner", "safe_calculator"],
    "security": ["security_scanner", "permission_checker", "secret_redactor"],
    "automation": ["function_router", "schema_validator", "n8n_webhook_optional"],
    "voice": ["groq_transcription", "voice_prompt_adapter"],
    "memory": ["memory_search", "memory_write", "vector_search"],
    "verification": ["schema_validator", "test_runner", "memory_search"],
    "data_analysis": ["data_parser", "sql_runner_optional", "chart_generator"],
    "compliance": ["policy_checker", "audit_log_reader", "evidence_tracker"],
    "edge_deployment": ["ollama_health", "device_profile", "local_model_runner"],
    "job_application": ["memory_search", "document_template", "ats_checker"],
    "semiconductor": ["memory_search", "document_parser", "structured_extractor"],
}


_SPECIALIZED_AGENT_NAMES = {
    "security": "Security Review Agent",
    "data_analysis": "Data Analysis Agent",
    "compliance": "Compliance Agent",
    "edge_deployment": "Edge Deployment Agent",
}


def _required_expertise(request: AutonomousAgentConstructionRequest) -> list[str]:
    text = _combined_request_text(request)
    expertise = [
        name
        for name, keywords in _EXPERTISE_KEYWORDS.items()
        if _contains_any(text, keywords)
    ]
    normalized_task_type = _normalize_agent_key(request.task_type)
    if normalized_task_type in _EXPERTISE_KEYWORDS:
        expertise.append(normalized_task_type)
    if request.security_requirements and "security" not in expertise:
        expertise.append("security")
    if request.memory_needs and "memory" not in expertise:
        expertise.append("memory")
    if _needs_verifier(expertise, text):
        expertise.append("verification")
    return _dedupe(expertise) or ["research"]


def _task_complexity(
    request: AutonomousAgentConstructionRequest,
    expertise: list[str],
) -> str:
    text = _combined_request_text(request)
    score = 1 + len(expertise)
    score += min(3, len(request.required_tools) // 2)
    score += 1 if request.memory_needs else 0
    score += 1 if request.privacy_level.lower() not in {"", "standard", "normal"} else 0
    score += 2 if "security" in expertise or request.security_requirements else 0
    score += 2 if request.context_size.lower() in {"large", "very large", "long"} else 0
    score += 2 if _contains_any(text, {"multi-agent", "distributed", "production", "scale"}) else 0
    if score <= 3:
        return "simple"
    if score <= 5:
        return "moderate"
    if score <= 8:
        return "complex"
    return "high_risk"


def _required_tools(
    request: AutonomousAgentConstructionRequest,
    expertise: list[str],
) -> list[str]:
    tools = [*request.required_tools]
    for area in expertise:
        tools.extend(_TOOLS_BY_EXPERTISE.get(area, ["memory_search"]))
    return _dedupe(tools) or ["memory_search"]


def _security_requirements(
    request: AutonomousAgentConstructionRequest,
    expertise: list[str],
) -> list[str]:
    requirements = [*request.security_requirements]
    privacy = request.privacy_level.lower()
    if privacy in {"private", "local", "confidential", "sensitive"}:
        requirements.append("keep sensitive context on approved local/private brains")
    if "security" in expertise:
        requirements.extend(
            [
                "redact secrets before external brain routing",
                "require explicit approval for risky tool side effects",
            ]
        )
    if "automation" in expertise:
        requirements.append("validate tool permissions before execution")
    return _dedupe(requirements)


def _memory_needs(
    request: AutonomousAgentConstructionRequest,
    expertise: list[str],
) -> list[str]:
    needs = [*request.memory_needs, "agent execution logs"]
    if "automation" in expertise:
        needs.append("successful workflows")
        needs.append("failed workflows")
    if "coding" in expertise:
        needs.append("code snippets")
    if "security" in expertise or "verification" in expertise:
        needs.append("failed workflows")
        needs.append("verification findings")
    if "memory" in expertise:
        needs.append("user preferences")
        needs.append("project history")
    return _dedupe(needs)


def _execution_cost(
    request: AutonomousAgentConstructionRequest,
    expertise: list[str],
    task_complexity: str,
) -> str:
    if request.execution_cost.lower() in {"low", "medium", "high"}:
        return request.execution_cost.lower()
    if request.speed_priority.lower() == "high" and request.privacy_level.lower() == "local":
        return "low"
    if task_complexity in {"complex", "high_risk"} or len(expertise) >= 4:
        return "high"
    if request.context_size.lower() in {"large", "very large", "long"}:
        return "high"
    return "medium"


def _definition_from_blueprint(blueprint: SaturnixAgentBlueprint) -> AutonomousAgentDefinition:
    return AutonomousAgentDefinition(
        agent_name=blueprint.agent_name,
        purpose=blueprint.purpose,
        best_brain=blueprint.best_brain,
        required_tools=blueprint.tools,
        workflow=[
            f"{step.order}. {step.name}: {step.description}"
            for step in blueprint.workflow_steps
        ],
        validation_rules=[
            f"{rule.name} ({rule.severity}): {rule.description}"
            for rule in blueprint.validation_rules
        ],
        memory_rules=[
            f"namespace: {blueprint.memory_rules.namespace}",
            f"recall: {blueprint.memory_rules.recall_policy}",
            f"write: {blueprint.memory_rules.write_policy}",
            f"retention: {blueprint.memory_rules.retention_policy}",
        ],
        fallback_logic=[
            f"fallback_brain: {blueprint.failure_handling.fallback_brain}",
            f"max_retries: {blueprint.failure_handling.max_retries}",
            f"retry_strategy: {blueprint.failure_handling.retry_strategy}",
            f"escalation: {blueprint.failure_handling.escalation_policy}",
        ],
    )


def _build_autonomous_definition(
    request: AutonomousAgentConstructionRequest,
    expertise: str,
    required_tools: list[str],
    security_requirements: list[str],
    memory_needs: list[str],
    route,
) -> AutonomousAgentDefinition:
    agent_name = _agent_name_for_expertise(expertise)
    scoped_tools = _dedupe(
        [
            *request.required_tools,
            *_TOOLS_BY_EXPERTISE.get(expertise, ["memory_search"]),
            "memory_search",
        ]
    )
    validation_rules = _autonomous_validation_rules(expertise, security_requirements)
    memory_namespace = f"agent:{_normalize_agent_key(agent_name)}"
    return AutonomousAgentDefinition(
        agent_name=agent_name,
        purpose=_purpose_for_expertise(expertise, request.task),
        best_brain=route.selected_brain,
        required_tools=scoped_tools or required_tools,
        workflow=[
            f"1. Analyze {expertise.replace('_', ' ')} boundaries, risks, and success criteria.",
            "2. Select only required tools and document permission-sensitive actions.",
            "3. Execute the specialized work with compact intermediate outputs.",
            "4. Validate output against format, safety, and task requirements.",
            "5. Store reusable decisions, failures, and optimization notes in memory.",
        ],
        validation_rules=validation_rules,
        memory_rules=[
            f"namespace: {memory_namespace}",
            "recall: retrieve prior agent designs, user preferences, and relevant failures",
            "write: store final blueprint, validation outcomes, and reusable strategies",
            f"memory_needs: {', '.join(memory_needs)}",
        ],
        fallback_logic=[
            f"fallback_brain: {route.fallback_brain}",
            "retry once with reduced scope and stricter acceptance criteria",
            "reuse default SATURNIX agents when specialized execution fails",
            "escalate with missing inputs, failed tool, and safest next action",
        ],
    )


def _autonomous_validation_rules(
    expertise: str,
    security_requirements: list[str],
) -> list[str]:
    rules = [
        "task_alignment (high): output must directly satisfy the requested specialization",
        "modularity (medium): agent responsibilities must not overlap existing agents",
        "tool_minimization (medium): use the smallest sufficient tool set",
    ]
    if expertise == "security" or security_requirements:
        rules.append("security_boundary (critical): enforce privacy and permission constraints")
    if expertise == "data_analysis":
        rules.append("data_integrity (high): preserve source fields, filters, and assumptions")
    if expertise == "compliance":
        rules.append("evidence_traceability (critical): separate policy facts from assumptions")
    if expertise == "edge_deployment":
        rules.append("local_resilience (high): support offline/local fallback behavior")
    return rules


def _coordination_workflow(agents: list[AutonomousAgentDefinition]) -> list[str]:
    if not agents:
        return ["No agent coordination required."]
    workflow = [
        f"{index}. {agent.agent_name} owns: {agent.purpose}"
        for index, agent in enumerate(agents, start=1)
    ]
    if len(agents) > 1:
        workflow.append(
            "Final handoff: consolidate outputs through the strongest verification-capable agent."
        )
    return workflow


def _scalability_notes(
    created_agents: list[AutonomousAgentDefinition],
    reused_agents: list[AutonomousAgentDefinition],
) -> list[str]:
    notes = [
        "Reuse defaults before creating new agents to prevent agent sprawl.",
        "Store dynamic agents in saturnix:agents for future deduplication.",
        "Keep agent responsibilities narrow so workflows can scale horizontally.",
    ]
    if created_agents:
        notes.append(
            "New agents should be promoted to defaults only after repeated successful use."
        )
    if reused_agents:
        notes.append(
            "Existing agents were reused to preserve stable capabilities and memory namespaces."
        )
    return notes


def _purpose_for_expertise(expertise: str, task: str) -> str:
    readable = expertise.replace("_", " ")
    return f"Handle {readable} specialization for task: {task}"


def _agent_name_for_expertise(expertise: str) -> str:
    if expertise in _SPECIALIZED_AGENT_NAMES:
        return _SPECIALIZED_AGENT_NAMES[expertise]
    return f"{expertise.replace('_', ' ').title()} Specialist Agent"


def _add_unique_agent(
    definition: AutonomousAgentDefinition,
    collection: list[AutonomousAgentDefinition],
    seen_agents: set[str],
) -> bool:
    key = _normalize_agent_key(definition.agent_name)
    if key in seen_agents:
        return False
    seen_agents.add(key)
    collection.append(definition)
    return True


def _needs_verifier(expertise: list[str], text: str) -> bool:
    if "verification" in expertise:
        return False
    if "security" in expertise or "automation" in expertise:
        return True
    if "coding" in expertise and _contains_any(text, {"production", "test", "verify"}):
        return True
    return len(expertise) >= 3


def _combined_request_text(request: AutonomousAgentConstructionRequest) -> str:
    parts = [
        request.task,
        request.task_type,
        request.privacy_level,
        request.speed_priority,
        request.context_size,
        request.output_format,
        " ".join(request.required_tools),
        " ".join(request.security_requirements),
        " ".join(request.memory_needs),
    ]
    return " ".join(parts).lower()


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _normalize_agent_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _name_from_task(task: str, task_type: str) -> str:
    if task_type.strip():
        base = task_type.strip()
    elif task.strip():
        base = task.strip().split(" ")[0]
    else:
        base = "custom"
    normalized = _normalize_agent_key(base)
    if normalized.endswith("_agent"):
        return normalized.replace("_", " ").title()
    return f"{normalized.replace('_', ' ').title()} Agent"


def _default_inputs_for_task(task_type: str) -> list[AgentInputDefinition]:
    normalized = task_type.lower()
    inputs = [
        AgentInputDefinition(name="task", description="Primary task or user goal."),
        AgentInputDefinition(
            name="context",
            description="Relevant files, documents, notes, transcripts, or prior outputs.",
            required=False,
        ),
        AgentInputDefinition(
            name="constraints",
            description="Privacy, speed, output, tool, or acceptance constraints.",
            required=False,
        ),
    ]
    if "voice" in normalized or "speech" in normalized:
        inputs[1] = AgentInputDefinition(
            name="audio_or_transcript",
            description="Audio input, audio file reference, or transcript.",
        )
    if "automation" in normalized:
        inputs.append(
            AgentInputDefinition(
                name="available_tools",
                description="Tool schemas, credentials, webhooks, or integration names.",
                required=False,
            )
        )
    return inputs


def _default_tools_for_task(task_type: str, selected_brain: str) -> list[str]:
    normalized = f"{task_type} {selected_brain}".lower()
    tools = ["memory_search"]
    if "coding" in normalized or "code" in normalized:
        tools.extend(["code_search", "test_runner"])
    if "gemini" in normalized or "automation" in normalized or "schema" in normalized:
        tools.extend(["schema_validator", "function_router"])
    if "voice" in normalized or "groq" in normalized:
        tools.extend(["groq_transcription", "voice_prompt_adapter"])
    if "ollama" in normalized:
        tools.append("local_model_runner")
    return list(dict.fromkeys(tools))


def _default_workflow_steps(task_type: str, task: str) -> list[AgentWorkflowStepDefinition]:
    normalized = f"{task_type} {task}".lower()
    if "automation" in normalized:
        return [
            AgentWorkflowStepDefinition(
                order=1,
                name="Map Automation Goal",
                description="Convert the request into triggers, actions, decisions, and outputs.",
                expected_output="Workflow map.",
            ),
            AgentWorkflowStepDefinition(
                order=2,
                name="Validate Tool Contracts",
                description="Check tool schemas, required inputs, and side-effect safety.",
                expected_output="Validated tool plan.",
            ),
            AgentWorkflowStepDefinition(
                order=3,
                name="Prepare Execution Plan",
                description="Return executable steps and rollback or escalation behavior.",
                expected_output="Execution-ready automation plan.",
            ),
        ]
    if "voice" in normalized or "speech" in normalized:
        return [
            AgentWorkflowStepDefinition(
                order=1,
                name="Normalize Voice Input",
                description="Transcribe or clean spoken input into reliable text.",
                expected_output="Clean transcript.",
            ),
            AgentWorkflowStepDefinition(
                order=2,
                name="Extract Intent",
                description="Map spoken intent into task, constraints, and response mode.",
                expected_output="Structured spoken intent.",
            ),
            AgentWorkflowStepDefinition(
                order=3,
                name="Generate Voice Response",
                description="Create concise output suitable for speech interaction.",
                expected_output="Voice-ready answer.",
            ),
        ]
    return [
        AgentWorkflowStepDefinition(
            order=1,
            name="Map Intent",
            description="Clarify objective, inputs, constraints, and success criteria.",
            expected_output="Intent map.",
        ),
        AgentWorkflowStepDefinition(
            order=2,
            name="Execute Specialized Work",
            description="Use the selected brain and tools to complete the task.",
            expected_output="Candidate output.",
        ),
        AgentWorkflowStepDefinition(
            order=3,
            name="Validate Output",
            description="Check format, completeness, safety, and task alignment.",
            expected_output="Validated final output.",
        ),
    ]


def _default_validation_rules(
    output_format: str,
    privacy_level: str,
    task_type: str,
) -> list[AgentValidationRule]:
    rules = [
        AgentValidationRule(
            name="task_alignment",
            description="Output must directly satisfy the stated purpose and task.",
            severity="high",
        ),
        AgentValidationRule(
            name="format_compliance",
            description=f"Output must match requested format: {output_format}.",
            severity="high",
        ),
    ]
    combined = f"{privacy_level} {task_type} {output_format}".lower()
    if any(token in combined for token in ["private", "local", "confidential", "sensitive"]):
        rules.append(
            AgentValidationRule(
                name="privacy_compliance",
                description=(
                    "Sensitive content must not be routed to external providers or stored "
                    "unsafely."
                ),
                severity="critical",
            )
        )
    if any(token in combined for token in ["json", "schema", "function"]):
        rules.append(
            AgentValidationRule(
                name="schema_validity",
                description="Structured outputs must be parseable and match the declared schema.",
                severity="critical",
            )
        )
    return rules


def _system_prompt_from_blueprint(blueprint: SaturnixAgentBlueprint) -> str:
    steps = "\n".join(
        f"{step.order}. {step.name}: {step.description}" for step in blueprint.workflow_steps
    )
    validation = "\n".join(
        f"- {rule.name} ({rule.severity}): {rule.description}"
        for rule in blueprint.validation_rules
    )
    return (
        f"You are {blueprint.agent_name} in SATURNIX-HARNESS.\n\n"
        f"Purpose: {blueprint.purpose}\n"
        f"Best brain: {blueprint.best_brain}\n"
        f"Output format: {blueprint.output_format}\n\n"
        f"Workflow:\n{steps}\n\n"
        f"Validation rules:\n{validation}\n\n"
        f"Memory policy: recall with '{blueprint.memory_rules.recall_policy}' and write with "
        f"'{blueprint.memory_rules.write_policy}'.\n"
        f"Failure handling: {blueprint.failure_handling.retry_strategy}; fallback brain is "
        f"{blueprint.failure_handling.fallback_brain}."
    )


def _capabilities_for_brain(best_brain: str) -> list[Capability]:
    normalized = best_brain.lower()
    if "claude" in normalized:
        return [Capability.reasoning, Capability.long_context, Capability.document_understanding]
    if "gemini" in normalized:
        return [Capability.structured_output, Capability.function_calling, Capability.reasoning]
    if "groq" in normalized:
        return [Capability.voice, Capability.realtime_speech, Capability.reasoning]
    if "ollama" in normalized and ("coding" in normalized or "minimax" in normalized):
        return [Capability.coding, Capability.local_private, Capability.reasoning]
    if "ollama" in normalized or "gemma" in normalized:
        return [Capability.local_private, Capability.reasoning]
    return [Capability.reasoning, Capability.planning, Capability.orchestration]


def _preferred_brain_for_name(best_brain: str) -> BrainName | None:
    normalized = best_brain.lower()
    if "claude" in normalized:
        return BrainName.claude
    if "gemini" in normalized:
        return BrainName.gemini
    if "groq" in normalized:
        return BrainName.groq
    if "ollama" in normalized and ("coding" in normalized or "minimax" in normalized):
        return BrainName.ollama_coding
    if "ollama" in normalized or "gemma" in normalized:
        return BrainName.ollama_gemma
    if "gpt" in normalized:
        return BrainName.openai
    return None
