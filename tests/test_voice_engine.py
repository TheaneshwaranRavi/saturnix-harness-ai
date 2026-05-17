import asyncio

from saturnix_harness.brains.mock_provider import MockProvider
from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.config import Settings
from saturnix_harness.schemas import (
    SaturnixExecutionResult,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
    VoiceTranscriptionResult,
)
from saturnix_harness.voice.engine import GROQ_SPEECH_URL, GROQ_TRANSCRIPTIONS_URL, VoiceEngine


def test_voice_command_extraction_routes_private_fast_code(tmp_path):
    engine = _engine(tmp_path)

    command = engine.extract_command("Hey Saturnix write private Python code quickly")

    assert command.command_text == "write private Python code quickly"
    assert command.task_type == "coding"
    assert command.privacy_level == "local"
    assert command.speed_priority == "high"
    assert command.output_format == "code"
    assert command.brain_routing["selected_brain"] == "MiniMax/Coding via Ollama"


def test_speech_to_text_uses_groq_transcriptions_endpoint(tmp_path, monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"text": "Design a SATURNIX workflow"}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, url, headers=None, files=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["files"] = files
            return FakeResponse()

    monkeypatch.setattr("saturnix_harness.voice.engine.httpx.AsyncClient", FakeClient)
    result = asyncio.run(_engine(tmp_path).speech_to_text(b"audio", filename="voice.wav"))

    assert captured["url"] == GROQ_TRANSCRIPTIONS_URL
    assert captured["headers"]["Authorization"] == "Bearer test-groq-key"
    assert captured["files"]["model"] == (None, "whisper-large-v3-turbo")
    assert result.text == "Design a SATURNIX workflow"


def test_text_to_speech_uses_groq_speech_endpoint(tmp_path, monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        content = b"audio-bytes"
        headers = {"content-type": "audio/wav"}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, url, headers=None, files=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("saturnix_harness.voice.engine.httpx.AsyncClient", FakeClient)
    result = asyncio.run(
        _engine(tmp_path).text_to_speech(VoiceSynthesisRequest(text="Hello SATURNIX"))
    )

    assert captured["url"] == GROQ_SPEECH_URL
    assert captured["headers"]["Authorization"] == "Bearer test-groq-key"
    assert captured["json"]["model"] == "canopylabs/orpheus-v1-english"
    assert captured["json"]["voice"] == "troy"
    assert result.audio_base64 == "YXVkaW8tYnl0ZXM="


def test_voice_workflow_routes_command_to_saturnix_core(tmp_path):
    engine = _engine(tmp_path)

    async def fake_speech_to_text(*args, **kwargs):
        return VoiceTranscriptionResult(
            text="Hey Saturnix design an automation workflow as JSON",
            model="whisper-large-v3-turbo",
            filename="voice.wav",
            raw={"text": "Hey Saturnix design an automation workflow as JSON"},
        )

    async def fake_text_to_speech(request):
        return VoiceSynthesisResult(
            text=request.text,
            model="canopylabs/orpheus-v1-english",
            voice="troy",
            response_format="wav",
            content_type="audio/wav",
            audio_base64="ZmFrZQ==",
        )

    async def fake_executor(request):
        assert request.goal == "design an automation workflow as JSON"
        assert request.task_type == "automation"
        assert request.output_format == "json schema"
        return SaturnixExecutionResult(
            goal=request.goal,
            detected_intent="automation workflow",
            agents_used=["saturnix_architect"],
            brain_routing={"selected_brain": "Gemini"},
            workflow=[],
            execution_result={"ok": True, "output": "Workflow created"},
            validation_result={"ok": True, "score": 1.0, "findings": []},
            memory_saved={},
            next_actions=["Review workflow"],
        )

    engine.speech_to_text = fake_speech_to_text
    engine.text_to_speech = fake_text_to_speech

    result = asyncio.run(
        engine.run_voice_workflow(
            audio=b"audio",
            filename="voice.wav",
            executor=fake_executor,
            synthesize_response=True,
        )
    )

    assert result.response_text == "Workflow created"
    assert result.tts is not None
    assert result.tts.audio_base64 == "ZmFrZQ=="


def _engine(tmp_path):
    settings = Settings(
        saturnix_env="test",
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
        saturnix_enable_chroma=False,
        groq_api_key="test-groq-key",
    )
    return VoiceEngine(
        settings=settings,
        brain_router=BrainRouter(settings, providers=[MockProvider(model="mock")]),
    )

