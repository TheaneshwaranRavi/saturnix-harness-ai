from saturnix_harness.brains.mock_provider import MockProvider
from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.config import Settings
from saturnix_harness.core.agent_constructor import AgentConstructor
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.schemas import AutonomousAgentConstructionRequest, DynamicAgentRequest
from saturnix_harness.tools.router import ToolRouter


def test_default_agents_include_required_blueprints(tmp_path):
    constructor = _constructor(tmp_path)

    agents = constructor.list_default_agents()
    names = {agent.agent_name for agent in agents}

    assert names == {
        "Research Agent",
        "Coding Agent",
        "Job Application Agent",
        "Semiconductor Agent",
        "Automation Agent",
        "Voice Agent",
        "Memory Agent",
        "Verification Agent",
    }
    for agent in agents:
        assert agent.purpose
        assert agent.best_brain
        assert agent.inputs
        assert agent.tools
        assert agent.workflow_steps
        assert agent.output_format
        assert agent.validation_rules
        assert agent.memory_rules.namespace
        assert agent.failure_handling.fallback_brain


def test_dynamic_constructor_selects_local_coding_brain(tmp_path):
    constructor = _constructor(tmp_path)

    blueprint = constructor.construct_blueprint(
        DynamicAgentRequest(
            task="Write a private Python parser",
            task_type="coding",
            privacy_level="local",
            speed_priority="high",
            context_size="small",
            output_format="code",
        )
    )

    assert blueprint.agent_name == "Coding Agent"
    assert blueprint.best_brain == "MiniMax/Coding via Ollama"
    assert "code_search" in blueprint.tools
    assert blueprint.memory_rules.namespace == "agent:coding_agent"


def test_dynamic_constructor_selects_gemini_for_schema_agent(tmp_path):
    constructor = _constructor(tmp_path)

    blueprint = constructor.construct_blueprint(
        DynamicAgentRequest(
            task="Create tool-call payloads for workflow automation",
            task_type="automation",
            privacy_level="standard",
            speed_priority="normal",
            context_size="medium",
            output_format="json schema",
        )
    )

    assert blueprint.best_brain == "Gemini"
    assert "schema_validator" in blueprint.tools
    assert any(rule.name == "schema_validity" for rule in blueprint.validation_rules)


def test_blueprint_converts_to_agent_spec(tmp_path):
    constructor = _constructor(tmp_path)
    blueprint = constructor.get_default_agent("voice_agent")

    spec = constructor.to_agent_spec(blueprint)

    assert spec.name == "voice_agent"
    assert spec.preferred_brain.value == "groq"
    assert "groq_transcription" in spec.tools
    assert spec.metadata["output_format"] == blueprint.output_format


def test_autonomous_constructor_reuses_existing_voice_agent(tmp_path):
    constructor = _constructor(tmp_path)

    result = constructor.construct_autonomous(
        AutonomousAgentConstructionRequest(
            task="Create a voice command flow for speech-to-text and text-to-speech",
            task_type="voice",
            required_tools=["groq_transcription"],
        )
    )

    reused_names = {agent.agent_name for agent in result.reused_agents}
    assert "Voice Agent" in reused_names
    assert result.created_agents == []
    assert "voice" in result.required_expertise
    assert "groq_transcription" in result.required_tools


def test_autonomous_constructor_creates_and_deduplicates_security_agent(tmp_path):
    constructor = _constructor(tmp_path)
    request = AutonomousAgentConstructionRequest(
        task="Threat model a private automation workflow with permissions and secrets",
        task_type="security",
        privacy_level="private",
        required_tools=["permission_checker"],
        security_requirements=["no external secrets"],
        memory_needs=["failed workflows"],
    )

    first = constructor.construct_autonomous(request)

    created_names = {agent.agent_name for agent in first.created_agents}
    reused_names = {agent.agent_name for agent in first.reused_agents}
    assert "Security Review Agent" in created_names
    assert "Automation Agent" in reused_names
    assert "Verification Agent" in reused_names
    assert first.memory_saved["created_count"] == 1
    assert first.memory_saved["created_agent_ids"]

    second = constructor.construct_autonomous(request)

    second_reused = {agent.agent_name for agent in second.reused_agents}
    assert second.created_agents == []
    assert "Security Review Agent" in second_reused
    assert "Security Review Agent" in second.duplicate_agents_avoided


def _constructor(tmp_path):
    settings = Settings(
        saturnix_env="test",
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
        saturnix_enable_chroma=False,
    )
    brain_router = BrainRouter(settings, providers=[MockProvider(model="mock")])
    return AgentConstructor(
        brain_router=brain_router,
        tool_router=ToolRouter(),
        memory=MemoryManager(settings),
    )
