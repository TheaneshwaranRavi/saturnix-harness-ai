from fastapi.testclient import TestClient

from saturnix_harness.api.dependencies import get_orchestrator
from saturnix_harness.config import Settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.core.self_healing_infrastructure import (
    SelfHealingInfrastructureEngine,
)
from saturnix_harness.main import app
from saturnix_harness.schemas import SelfHealingInfrastructureRequest


def test_self_healing_reports_healthy_system():
    result = SelfHealingInfrastructureEngine().diagnose(
        SelfHealingInfrastructureRequest()
    )

    assert result.overall_status == "healthy"
    assert result.health_score == 100
    assert result.incidents_detected == []
    assert result.recovery_actions == []
    assert result.notifications == [
        "SATURNIX infrastructure is healthy; no recovery actions required."
    ]


def test_self_healing_detects_failures_and_recovery_actions():
    result = SelfHealingInfrastructureEngine().diagnose(
        SelfHealingInfrastructureRequest(
            containers={"saturnix-api": "crashed", "ollama": "oom killed"},
            apis={"openai": "timeout", "gemini": "503"},
            memory_usage_percent=94,
            disk_usage_percent=98,
            network_status="degraded",
            workflows={"agent-build": "corrupted"},
            processes={"worker-7": "hanging for 300s"},
            active_brain="GPT",
            fallback_brains=["Claude", "Gemini", "Gemma via Ollama"],
            auto_recover=True,
        )
    )

    action_names = {action.action for action in result.recovery_actions}
    failure_types = {incident.failure_type for incident in result.incidents_detected}

    assert result.overall_status == "critical"
    assert result.health_score < 50
    assert "crashed_container" in failure_types
    assert "failed_api" in failure_types
    assert "memory_overload" in failure_types
    assert "disk_failure" in failure_types
    assert "corrupted_workflow" in failure_types
    assert "hanging_process" in failure_types
    assert "restart_service" in action_names
    assert "switch_fallback_brain" in action_names
    assert "recover_memory" in action_names
    assert "isolate_faulty_module" in action_names
    assert "rebuild_failed_workflow" in action_names
    assert result.fallback_brain == "Claude"
    assert any("agent-build" in item for item in result.workflow_rebuilds)
    assert any("Critical components" in item for item in result.notifications)


def test_self_healing_api_endpoint(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    try:
        response = client.post(
            "/v1/self-healing/diagnose",
            json={
                "containers": {"voice-engine": "unhealthy"},
                "apis": {"groq": "down"},
                "network_status": "offline",
                "processes": {"voice-worker": "stuck"},
                "active_brain": "Groq",
                "fallback_brains": ["GPT", "Claude"],
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {
            "overall_status",
            "health_score",
            "incidents_detected",
            "recovery_actions",
            "fallback_brain",
            "isolation_plan",
            "workflow_rebuilds",
            "notifications",
            "resilience_plan",
        }
        assert payload["overall_status"] in {"degraded", "critical"}
        assert payload["fallback_brain"] == "GPT"
        assert payload["incidents_detected"]
        assert payload["recovery_actions"]
    finally:
        app.dependency_overrides.clear()


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_mock_brains=True,
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "self_healing.sqlite3",
    )
