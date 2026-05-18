import asyncio

from fastapi.testclient import TestClient

from saturnix_harness.api.dependencies import get_orchestrator
from saturnix_harness.config import Settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.main import app
from saturnix_harness.schemas import OmegaRunRequest


def test_omega_engine_runs_cognitive_os_loop(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    result = asyncio.run(
        orchestrator.run_omega(
            OmegaRunRequest(
                goal="Build a secure multi-agent coding workflow with verification",
                input=(
                    "Use memory, brain routing, recursive improvement, "
                    "and infrastructure checks."
                ),
                task_type="coding architecture",
                privacy_level="standard",
                use_consensus=False,
            )
        )
    )

    payload = result.model_dump()
    assert payload["operating_mode"] == "SATURNIX-HARNESS OMEGA"
    assert payload["detected_intent"]["summary"]
    assert (
        payload["autonomous_agents"]["reused_agents"]
        or payload["autonomous_agents"]["created_agents"]
    )
    assert payload["brain_routing"]["selected_brain"]
    assert payload["tool_routing"]["selected_tools"]
    assert payload["workflow_plan"]["execution_graph"]["nodes"]
    assert payload["security_scan"]["security_score"]
    assert payload["execution_result"]["ok"] is True
    assert payload["verification_result"]["ok"] is True
    assert payload["recursive_improvement"]["optimization_report"]
    assert payload["long_term_memory"]["memory"]["namespace"] == "saturnix:omega"
    assert payload["infrastructure_optimization"]["distributed"]["node_assignments"]
    assert payload["evolution_plan"]
    assert payload["next_actions"]


def test_omega_engine_supports_planned_only_consensus_mode(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    result = asyncio.run(
        orchestrator.run_omega(
            OmegaRunRequest(
                goal="Plan a private local automation system without executing it",
                task_type="automation",
                privacy_level="private",
                local_only=True,
                execute=False,
                use_consensus=True,
                persist_memory=False,
                optimize_infrastructure=False,
            )
        )
    )

    assert result.execution_result["mode"] == "planned_only"
    assert result.consensus is not None
    assert result.long_term_memory == {}
    assert result.infrastructure_optimization["distributed"] is None
    assert "Ollama" in result.brain_routing["selected_brain"]
    assert any("local" in item.lower() for item in result.evolution_plan)


def test_omega_api_endpoint(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    try:
        response = client.post(
            "/v1/omega/run",
            json={
                "goal": "Design an autonomous research agent system",
                "task_type": "architecture",
                "execute": False,
                "use_consensus": False,
                "persist_memory": False,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {
            "goal",
            "operating_mode",
            "detected_intent",
            "autonomous_agents",
            "brain_routing",
            "tool_routing",
            "workflow_plan",
            "security_scan",
            "consensus",
            "execution_result",
            "verification_result",
            "recursive_improvement",
            "long_term_memory",
            "infrastructure_optimization",
            "evolution_plan",
            "next_actions",
        }
        assert payload["operating_mode"] == "SATURNIX-HARNESS OMEGA"
        assert payload["execution_result"]["mode"] == "planned_only"
        assert payload["workflow_plan"]["critical_path"]
    finally:
        app.dependency_overrides.clear()


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_mock_brains=True,
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "omega.sqlite3",
    )
