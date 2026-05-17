from fastapi.testclient import TestClient

from saturnix_harness.api.dependencies import get_orchestrator
from saturnix_harness.config import Settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.main import app


def test_phase1_root_endpoints_and_sqlite_tables(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    try:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        agents = client.get("/agents")
        assert agents.status_code == 200
        agent_names = {agent["agent_name"] for agent in agents.json()}
        assert agent_names == {
            "Research Agent",
            "Coding Agent",
            "Automation Agent",
            "Voice Agent",
            "Memory Agent",
            "Verification Agent",
        }

        brains = client.get("/brains")
        assert brains.status_code == 200
        assert isinstance(brains.json(), list)

        execute = client.post(
            "/execute",
            json={
                "goal": "Design a Phase 1 SATURNIX research workflow with verification",
                "task_type": "architecture",
                "privacy_level": "standard",
                "speed_priority": "normal",
                "context_size": "medium",
                "output_format": "markdown",
            },
        )
        assert execute.status_code == 200
        payload = execute.json()
        assert payload["goal"].startswith("Design a Phase 1")
        assert payload["detected_intent"]
        assert payload["agents_used"]
        assert payload["brain_routing"]
        assert payload["workflow"]
        assert payload["execution_result"]["ok"] is True
        assert payload["memory_saved"]["phase1_tables"]["user_goal_id"]

        counts = orchestrator.memory.phase1_table_counts()
        assert counts["user_goals"] == 1
        assert counts["agent_runs"] >= 1
        assert counts["brain_routes"] == 1
        assert counts["verification_results"] == 1
    finally:
        app.dependency_overrides.clear()


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_mock_brains=True,
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "phase1.sqlite3",
    )

