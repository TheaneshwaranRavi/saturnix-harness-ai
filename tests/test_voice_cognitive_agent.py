import asyncio

from fastapi.testclient import TestClient

from saturnix_harness.api.dependencies import get_orchestrator
from saturnix_harness.config import Settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.main import app
from saturnix_harness.schemas import (
    MemoryType,
    SaturnixExecutionResult,
    SaveMemoryRequest,
    VoiceCognitiveTurnRequest,
)


def test_voice_cognitive_agent_executes_with_memory_context(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))
    session_id = "session-memory"
    orchestrator.memory.save_memory(
        SaveMemoryRequest(
            content="assistant: Previous plan used local Ollama for private tasks.",
            memory_type=MemoryType.agent_execution_logs,
            namespace=f"saturnix:voice:{session_id}",
            kind="voice_assistant_turn",
            tags=["voice", "conversation"],
        )
    )

    async def fake_executor(request):
        assert "Previous plan used local Ollama" in request.input
        return _execution_result(request.goal, output="Memory-aware workflow executed")

    result = asyncio.run(
        orchestrator.voice_cognitive_agent.run_turn(
            VoiceCognitiveTurnRequest(
                transcript="Hey Saturnix continue the private workflow plan",
                session_id=session_id,
            ),
            fake_executor,
        )
    )

    assert result.session_id == session_id
    assert result.command is not None
    assert result.memory_context
    assert result.execution_result is not None
    assert result.response_text == "Memory-aware workflow executed"
    assert result.stage_timings_ms["total_ms"] >= 0
    assert result.memory_saved["namespace"] == f"saturnix:voice:{session_id}"


def test_voice_cognitive_agent_requires_confirmation_for_risky_actions(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))
    calls = []

    async def fake_executor(request):
        calls.append(request)
        return _execution_result(request.goal, output="Risky action executed")

    first = asyncio.run(
        orchestrator.voice_cognitive_agent.run_turn(
            VoiceCognitiveTurnRequest(
                transcript="Saturnix delete the production database",
                session_id="session-risk",
            ),
            fake_executor,
        )
    )

    assert first.confirmation_required is True
    assert first.confirmation_token
    assert first.execution_result is None
    assert calls == []

    second = asyncio.run(
        orchestrator.voice_cognitive_agent.run_turn(
            VoiceCognitiveTurnRequest(
                transcript="yes proceed",
                session_id="session-risk",
                confirmation_token=first.confirmation_token,
                confirmed=True,
            ),
            fake_executor,
        )
    )

    assert len(calls) == 1
    assert second.execution_result is not None
    assert second.response_text == "Risky action executed"
    assert second.memory_saved["confirmed_pending_record_id"]


def test_voice_cognitive_agent_interrupts_pending_command(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    async def fake_executor(request):
        raise AssertionError("interrupted voice command should not execute")

    first = asyncio.run(
        orchestrator.voice_cognitive_agent.run_turn(
            VoiceCognitiveTurnRequest(
                transcript="Saturnix push and deploy to production",
                session_id="session-stop",
            ),
            fake_executor,
        )
    )
    assert first.confirmation_required is True

    interrupted = asyncio.run(
        orchestrator.voice_cognitive_agent.run_turn(
            VoiceCognitiveTurnRequest(
                transcript="stop",
                session_id="session-stop",
                confirmation_token=first.confirmation_token,
            ),
            fake_executor,
        )
    )

    assert interrupted.interrupted is True
    assert interrupted.execution_result is None
    assert "interrupted" in interrupted.response_text.lower()


def test_voice_cognitive_turn_api_requires_confirmation(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    try:
        response = client.post(
            "/v1/voice/cognitive/turn",
            json={
                "transcript": "Saturnix send the customer data by email",
                "session_id": "api-risk",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["confirmation_required"] is True
        assert payload["risk_assessment"]["risk_level"] in {"high", "critical"}
        assert payload["execution_result"] is None
        assert payload["confirmation_token"]
    finally:
        app.dependency_overrides.clear()


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_mock_brains=True,
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "voice_cognitive.sqlite3",
    )


def _execution_result(goal: str, output: str):
    return SaturnixExecutionResult(
        goal=goal,
        detected_intent="voice cognitive command",
        agents_used=["Voice Agent"],
        brain_routing={"selected_brain": "GPT"},
        workflow=[],
        execution_result={"ok": True, "output": output, "traces": []},
        validation_result={"ok": True, "score": 1.0, "findings": []},
        memory_saved={},
        next_actions=[],
    )
