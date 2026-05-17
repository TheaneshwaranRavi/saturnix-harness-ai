from fastapi.testclient import TestClient

from saturnix_harness.api.dependencies import get_orchestrator
from saturnix_harness.config import Settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.main import app
from saturnix_harness.schemas import ToolRoutingRequest
from saturnix_harness.tools.intelligence_router import ToolIntelligenceRouter


def test_tool_intelligence_router_prefers_private_local_tools():
    result = ToolIntelligenceRouter().route(
        ToolRoutingRequest(
            task="Analyze private code snippets and recall previous security patterns",
            task_type="coding memory",
            speed_requirement="high",
            privacy_level="private",
            execution_cost="low",
            reliability_requirement="high",
            scalability_requirement="medium",
            constraints=["offline", "semantic retrieval"],
        )
    )

    assert "local_python" in result.selected_tools
    assert "vector_memory" in result.selected_tools
    assert "file_systems" in result.selected_tools
    assert "web_search" not in result.selected_tools
    assert result.tool_reasoning
    assert result.fallback_tools


def test_tool_intelligence_router_selects_voice_and_edge_tools():
    result = ToolIntelligenceRouter().route(
        ToolRoutingRequest(
            task="Process voice commands on a Raspberry Pi edge node for offline sensors",
            task_type="voice edge iot",
            speed_requirement="normal",
            privacy_level="local",
            execution_cost="balanced",
            reliability_requirement="standard",
            scalability_requirement="medium",
            constraints=["offline"],
        )
    )

    assert "raspberry_pi_edge_node" in result.selected_tools
    assert "voice_systems" in result.selected_tools or "voice_systems" in result.fallback_tools
    assert any("raspberry_pi_edge_node" in reason for reason in result.tool_reasoning)


def test_tool_intelligence_router_api_endpoint(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    try:
        response = client.post(
            "/v1/tools/route",
            json={
                "task": "Update GitHub issues and query project database",
                "task_type": "automation",
                "privacy_level": "standard",
                "speed_requirement": "normal",
                "reliability_requirement": "high",
                "scalability_requirement": "high",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {"selected_tools", "tool_reasoning", "fallback_tools"}
        assert "github" in payload["selected_tools"]
        assert "databases" in payload["selected_tools"]
    finally:
        app.dependency_overrides.clear()


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_mock_brains=True,
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "tool_router.sqlite3",
    )
