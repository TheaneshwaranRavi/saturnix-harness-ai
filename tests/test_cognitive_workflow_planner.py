from fastapi.testclient import TestClient

from saturnix_harness.api.dependencies import get_orchestrator
from saturnix_harness.brains.mock_provider import MockProvider
from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.config import Settings
from saturnix_harness.core.agent_constructor import AgentConstructor
from saturnix_harness.core.cognitive_workflow_planner import CognitiveWorkflowPlanner
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.main import app
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.schemas import CognitiveWorkflowPlanRequest
from saturnix_harness.tools.router import ToolRouter


def test_cognitive_workflow_planner_builds_dependency_graph(tmp_path):
    planner = _planner(tmp_path)

    result = planner.plan(
        CognitiveWorkflowPlanRequest(
            goal=(
                "Build a private FastAPI automation workflow with JSON schema, "
                "memory, security review, and verification"
            ),
            privacy_level="private",
            output_format="json schema",
        )
    )

    node_ids = {node["id"] for node in result.execution_graph["nodes"]}
    assert {"intent", "architecture", "implementation", "automation", "security"}.issubset(
        node_ids
    )
    assert result.workflow_tree.id == "intent"
    assert result.critical_path[0] == "intent"
    assert "verification" in result.critical_path
    assert result.parallel_execution_opportunities
    assert result.estimated_execution_cost in {"medium", "high", "very_high"}
    assert result.estimated_runtime_seconds > 0
    assert result.memory_saved["namespace"] == "saturnix:workflow_plans"


def test_cognitive_workflow_planner_assigns_local_brain_for_private_steps(tmp_path):
    planner = _planner(tmp_path)

    result = planner.plan(
        CognitiveWorkflowPlanRequest(
            goal="Plan private local coding with Ollama and verification",
            task_type="coding",
            privacy_level="private",
            output_format="markdown",
            persist_plan=False,
        )
    )

    implementation = next(
        node for node in result.execution_graph["nodes"] if node["id"] == "implementation"
    )
    assert implementation["assigned_agent"] == "Coding Agent"
    assert "Ollama" in implementation["assigned_brain"]
    assert result.memory_saved == {}


def test_cognitive_workflow_planner_api_endpoint(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    try:
        response = client.post(
            "/v1/workflows/plan",
            json={
                "goal": "Plan a research and verification workflow for documents",
                "task_type": "research",
                "context": "Long source material will arrive later.",
                "privacy_level": "standard",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["workflow_tree"]
        assert payload["execution_graph"]["nodes"]
        assert payload["critical_path"]
        assert "estimated_runtime" in payload
    finally:
        app.dependency_overrides.clear()


def _planner(tmp_path):
    settings = _settings(tmp_path)
    brain_router = BrainRouter(settings, providers=[MockProvider(model="mock")])
    memory = MemoryManager(settings)
    return CognitiveWorkflowPlanner(
        brain_router=brain_router,
        agent_constructor=AgentConstructor(brain_router, ToolRouter(), memory),
        memory=memory,
    )


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_mock_brains=True,
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "workflow_planner.sqlite3",
    )
