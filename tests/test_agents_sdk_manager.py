import asyncio

from fastapi.testclient import TestClient

from saturnix_harness.api.dependencies import get_orchestrator
from saturnix_harness.config import Settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.main import app
from saturnix_harness.schemas import SaturnixAgentRunRequest


def test_sdk_agent_registry_and_handoff_plan(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    agents = orchestrator.sdk_agent_manager.registry_entries()
    names = {agent.agent_name for agent in agents}

    assert "Personal Assistant Agent" in names
    assert "Voice Agent" in names
    assert "Verification Agent" in names
    assert len(agents) >= 10

    plan = orchestrator.sdk_agent_manager.handoff_plan()
    assert plan.execution_order == [
        "Voice Agent",
        "Research Agent",
        "Coding Agent",
        "Verification Agent",
        "Memory Agent",
    ]


def test_sdk_agent_dry_run_uses_structured_output(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    result = asyncio.run(
        orchestrator.run_sdk_agent(
            SaturnixAgentRunRequest(
                agent_name="Research Agent",
                goal="Research SATURNIX secure dashboard architecture",
                dry_run=True,
            )
        )
    )

    assert result.ok is True
    assert result.output is not None
    assert result.output.summary
    assert result.guardrail.allowed is True
    assert result.trace_events


def test_sdk_agent_blocks_risky_non_approved_action(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    result = asyncio.run(
        orchestrator.run_sdk_agent(
            SaturnixAgentRunRequest(
                agent_name="Security Agent",
                goal="Execute an admin security workflow",
                dry_run=False,
                approved=False,
            )
        )
    )

    assert result.ok is False
    assert result.guardrail.approval_required is True
    assert "human_approval_for_risky_actions" in result.guardrail.principles_enforced


def test_sdk_dashboard_routes(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    try:
        registry = client.get("/agents/registry")
        assert registry.status_code == 200
        assert registry.json()["agents"]

        sdk_agents = client.get("/v1/sdk/agents")
        assert sdk_agents.status_code == 200
        assert sdk_agents.json()["sdk_status"]["enabled"] is True

        handoffs = client.get("/v1/sdk/handoffs")
        assert handoffs.status_code == 200
        assert handoffs.json()["execution_order"][0] == "Voice Agent"

        traces = client.get("/dashboard/traces")
        assert traces.status_code == 200
        assert "events" in traces.json()
    finally:
        app.dependency_overrides.clear()


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_mock_brains=True,
        saturnix_enable_chroma=False,
        saturnix_enable_agents_sdk=True,
        saturnix_dashboard_auth_required=False,
        saturnix_sqlite_path=tmp_path / "agents_sdk.sqlite3",
        saturnix_agents_session_path=tmp_path / "agents_sessions.sqlite3",
    )
