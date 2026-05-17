import asyncio

from saturnix_harness.brains.mock_provider import MockProvider
from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.config import Settings
from saturnix_harness.core.agent_constructor import AgentConstructor
from saturnix_harness.core.execution_engine import SaturnixExecutionEngine
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.core.verification_engine import VerificationEngine
from saturnix_harness.core.workflow import NavigationWorkflowBuilder
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.monitoring.events import MonitoringLayer
from saturnix_harness.schemas import SaturnixExecutionRequest
from saturnix_harness.tools.router import ToolRouter


def test_saturnix_execution_engine_returns_required_schema(tmp_path):
    orchestrator = _orchestrator(tmp_path)

    result = asyncio.run(
        orchestrator.execute_goal(
            SaturnixExecutionRequest(
                goal="Design a small agent workflow with validation",
                task_type="architecture",
                privacy_level="standard",
                speed_priority="normal",
                context_size="medium",
                output_format="markdown",
            )
        )
    )
    payload = result.model_dump()

    assert set(payload) == {
        "goal",
        "detected_intent",
        "agents_used",
        "brain_routing",
        "workflow",
        "execution_result",
        "validation_result",
        "memory_saved",
        "next_actions",
    }
    assert payload["goal"] == "Design a small agent workflow with validation"
    assert payload["detected_intent"]
    assert payload["agents_used"]
    assert payload["brain_routing"]["selected_brain"] == "GPT"
    assert payload["workflow"]
    assert payload["execution_result"]["ok"] is True
    assert payload["validation_result"]["ok"] is True
    assert payload["memory_saved"]["namespace"] == "saturnix:execution"
    assert payload["next_actions"]


def test_saturnix_execution_engine_returns_structured_failure(tmp_path):
    settings = _settings(tmp_path)
    brain_router = BrainRouter(settings, providers=[MockProvider(model="mock")])
    tool_router = ToolRouter()
    memory = MemoryManager(settings)

    class BrokenIntentMapper:
        def map(self, request):
            raise RuntimeError("intent mapper unavailable")

    engine = SaturnixExecutionEngine(
        intent_mapper=BrokenIntentMapper(),
        brain_router=brain_router,
        agent_constructor=AgentConstructor(brain_router, tool_router, memory),
        workflow_builder=NavigationWorkflowBuilder(),
        verifier=VerificationEngine(brain_router),
        tool_router=tool_router,
        memory=memory,
        monitoring=MonitoringLayer(),
    )

    result = asyncio.run(
        engine.execute_goal(SaturnixExecutionRequest(goal="This should fail cleanly"))
    )

    assert result.execution_result["ok"] is False
    assert "intent mapper unavailable" in result.execution_result["error"]
    assert result.validation_result["ok"] is False
    assert result.memory_saved["recursive_improvement_strategy_ids"]
    assert result.next_actions


def _orchestrator(tmp_path):
    return CoreOrchestrator(settings=_settings(tmp_path))


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_mock_brains=True,
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
    )
