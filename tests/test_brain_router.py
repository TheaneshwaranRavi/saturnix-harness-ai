import asyncio

from saturnix_harness.brains.mock_provider import MockProvider
from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.config import Settings
from saturnix_harness.schemas import BrainMessage, BrainName, BrainRequest, BrainRouteRequest, Capability


def test_router_selects_mock_when_only_provider(tmp_path):
    settings = Settings(
        saturnix_env="test",
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
        saturnix_enable_chroma=False,
    )
    router = BrainRouter(settings, providers=[MockProvider(model="mock")])

    decision = router.route(
        BrainRequest(
            messages=[BrainMessage(role="user", content="Plan a workflow")],
            required_capabilities=[Capability.planning],
        )
    )

    assert decision.selected == BrainName.mock


def test_router_completes_with_mock(tmp_path):
    settings = Settings(
        saturnix_env="test",
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
        saturnix_enable_chroma=False,
    )
    router = BrainRouter(settings, providers=[MockProvider(model="mock")])

    response = asyncio.run(
        router.complete(
            BrainRequest(
                messages=[BrainMessage(role="user", content="Build an agent")],
                required_capabilities=[Capability.reasoning],
            )
        )
    )

    assert response.provider == BrainName.mock
    assert "SATURNIX mock brain response" in response.content


def test_task_router_selects_gpt_for_architecture(tmp_path):
    router = _router(tmp_path)

    decision = router.route_task(
        BrainRouteRequest(
            task="Design the architecture for a multi-agent planning system",
            task_type="architecture",
            privacy_level="standard",
            speed_priority="normal",
            context_size="medium",
            output_format="markdown",
        )
    )

    assert decision.selected_brain == "GPT"
    assert decision.fallback_brain == "Claude"


def test_task_router_selects_claude_for_large_documents(tmp_path):
    router = _router(tmp_path)

    decision = router.route_task(
        BrainRouteRequest(
            task="Analyze a 200 page contract",
            task_type="deep analysis",
            privacy_level="standard",
            speed_priority="normal",
            context_size="large",
            output_format="summary",
        )
    )

    assert decision.selected_brain == "Claude"


def test_task_router_selects_gemini_for_schema_output(tmp_path):
    router = _router(tmp_path)

    decision = router.route_task(
        BrainRouteRequest(
            task="Return valid structured data for tool execution",
            task_type="function calling",
            privacy_level="standard",
            speed_priority="normal",
            context_size="small",
            output_format="json schema",
        )
    )

    assert decision.selected_brain == "Gemini"


def test_task_router_selects_gemma_for_private_lightweight_task(tmp_path):
    router = _router(tmp_path)

    decision = router.route_task(
        BrainRouteRequest(
            task="Summarize this private note",
            task_type="lightweight",
            privacy_level="private",
            speed_priority="normal",
            context_size="small",
            output_format="text",
        )
    )

    assert decision.selected_brain == "Gemma via Ollama"


def test_task_router_selects_ollama_coding_for_fast_local_code(tmp_path):
    router = _router(tmp_path)

    decision = router.route_task(
        BrainRouteRequest(
            task="Write a Python helper function",
            task_type="coding",
            privacy_level="local",
            speed_priority="high",
            context_size="small",
            output_format="code",
        )
    )

    assert decision.selected_brain == "MiniMax/Coding via Ollama"


def test_task_router_selects_groq_for_voice(tmp_path):
    router = _router(tmp_path)

    decision = router.route_task(
        BrainRouteRequest(
            task="Transcribe audio and respond with voice",
            task_type="speech-to-text",
            privacy_level="standard",
            speed_priority="realtime",
            context_size="small",
            output_format="audio",
        )
    )

    assert decision.selected_brain == "Groq"


def _router(tmp_path):
    settings = Settings(
        saturnix_env="test",
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
        saturnix_enable_chroma=False,
    )
    return BrainRouter(settings, providers=[MockProvider(model="mock")])
