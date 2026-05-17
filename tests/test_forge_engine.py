from fastapi.testclient import TestClient

from saturnix_harness.api.dependencies import get_orchestrator
from saturnix_harness.config import Settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.main import app
from saturnix_harness.schemas import ForgeBuildRequest


def test_forge_coding_engine_generates_production_foundation(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    result = orchestrator.forge_engine.build(
        ForgeBuildRequest(
            goal="Build a FastAPI backend with database persistence and monitoring",
            project_name="Forge CRM",
            stack=["Python", "FastAPI", "SQLite"],
            features=["contacts", "audit logs"],
            scalability_target="high",
        )
    )

    assert result.architecture_plan.summary.startswith("Build Forge CRM")
    assert result.architecture_plan.selected_brain
    assert "docker" in result.architecture_plan.selected_tools
    assert any(item.path.endswith("backend/app/main.py") for item in result.folder_structure)
    assert any(artifact.path.endswith("backend/app/main.py") for artifact in result.implementation)
    assert any("FastAPI" in artifact.content for artifact in result.implementation)
    assert any(test.path.endswith("tests/test_health.py") for test in result.tests)
    assert result.deployment_setup.artifacts
    assert result.monitoring_setup.health_checks
    assert result.optimization_report
    assert result.memory_saved["namespace"] == "saturnix:forge"


def test_forge_coding_engine_respects_disabled_optional_layers(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    result = orchestrator.forge_engine.build(
        ForgeBuildRequest(
            goal="Build a small private CLI helper",
            project_name="Local Helper",
            application_type="cli",
            privacy_level="private",
            include_database=False,
            include_docker=False,
            include_ci=False,
            include_monitoring=False,
            persist_plan=False,
        )
    )

    paths = [item.path for item in result.folder_structure]
    assert not any("/db" in path for path in paths)
    assert result.deployment_setup.artifacts == []
    assert result.memory_saved == {}
    assert "Ollama" in result.architecture_plan.selected_brain
    assert result.monitoring_setup.logs == []


def test_forge_build_api_endpoint(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    try:
        response = client.post(
            "/v1/forge/build",
            json={
                "goal": "Build a fullstack API dashboard with Docker and CI",
                "project_name": "Ops Dashboard",
                "application_type": "fullstack",
                "features": ["dashboard", "alerts"],
                "include_frontend": True,
                "scalability_target": "high",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {
            "architecture_plan",
            "folder_structure",
            "implementation",
            "tests",
            "deployment_setup",
            "monitoring_setup",
            "optimization_report",
            "memory_saved",
        }
        assert payload["architecture_plan"]["components"]
        assert any("frontend/src" in item["path"] for item in payload["folder_structure"])
        assert payload["deployment_setup"]["release_checks"]
    finally:
        app.dependency_overrides.clear()


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_mock_brains=True,
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "forge.sqlite3",
    )
