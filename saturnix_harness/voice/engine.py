from __future__ import annotations

import base64
import logging
from collections.abc import Awaitable, Callable

import httpx

from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.config import Settings
from saturnix_harness.exceptions import ConfigurationError
from saturnix_harness.prompts import load_prompt
from saturnix_harness.schemas import (
    BrainMessage,
    BrainRequest,
    BrainRouteRequest,
    Capability,
    SaturnixExecutionRequest,
    SaturnixExecutionResult,
    VoiceCommand,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
    VoiceTranscriptionResult,
    VoiceWorkflowResult,
)

logger = logging.getLogger(__name__)

GROQ_TRANSCRIPTIONS_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_SPEECH_URL = "https://api.groq.com/openai/v1/audio/speech"


class VoiceEngine:
    """Groq-backed SATURNIX voice engine.

    Workflow:
    Voice input -> Groq STT -> command extraction -> SATURNIX execution ->
    response text -> Groq TTS.
    """

    def __init__(self, settings: Settings, brain_router: BrainRouter) -> None:
        self.settings = settings
        self.brain_router = brain_router

    def _headers(self) -> dict[str, str]:
        if not self.settings.has_secret(self.settings.groq_api_key):
            raise ConfigurationError("GROQ_API_KEY is required for SATURNIX voice features.")
        return {"Authorization": f"Bearer {self.settings.groq_api_key.get_secret_value()}"}

    async def transcribe_bytes(self, audio: bytes, filename: str = "audio.wav") -> dict:
        return (await self.speech_to_text(audio, filename=filename)).model_dump(mode="json")

    async def speech_to_text(
        self,
        audio: bytes,
        filename: str = "audio.wav",
        language: str | None = None,
        prompt: str | None = None,
        response_format: str = "json",
    ) -> VoiceTranscriptionResult:
        if not self.settings.has_secret(self.settings.groq_api_key):
            raise ConfigurationError("GROQ_API_KEY is required for voice transcription.")
        files = {
            "file": (filename, audio),
            "model": (None, self.settings.groq_transcription_model),
            "response_format": (None, response_format),
        }
        if language:
            files["language"] = (None, language)
        if prompt:
            files["prompt"] = (None, prompt)
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                GROQ_TRANSCRIPTIONS_URL,
                headers=self._headers(),
                files=files,
            )
        if response.status_code >= 400:
            raise ConfigurationError(f"Groq transcription failed: {response.status_code} {response.text}")
        if response_format == "text":
            text = response.text
            raw: dict = {"text": text}
        else:
            raw = response.json()
            text = raw.get("text", "")
        logger.info("Groq STT completed for %s with %s characters.", filename, len(text))
        return VoiceTranscriptionResult(
            text=text,
            model=self.settings.groq_transcription_model,
            filename=filename,
            language=language,
            raw=raw,
        )

    async def text_to_speech(self, request: VoiceSynthesisRequest) -> VoiceSynthesisResult:
        model = request.model or self.settings.groq_tts_model
        voice = request.voice or self.settings.groq_tts_voice
        response_format = request.response_format or self.settings.groq_tts_response_format
        payload = {
            "model": model,
            "input": request.text,
            "voice": voice,
            "response_format": response_format,
        }
        headers = {**self._headers(), "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                GROQ_SPEECH_URL,
                headers=headers,
                json=payload,
            )
        if response.status_code >= 400:
            raise ConfigurationError(f"Groq text-to-speech failed: {response.status_code} {response.text}")
        content_type = response.headers.get("content-type", f"audio/{response_format}")
        logger.info("Groq TTS completed with model=%s voice=%s.", model, voice)
        return VoiceSynthesisResult(
            text=request.text,
            model=model,
            voice=voice,
            response_format=response_format,
            content_type=content_type,
            audio_base64=base64.b64encode(response.content).decode("ascii"),
        )

    def extract_command(self, transcript: str) -> VoiceCommand:
        command_text = _clean_command_text(transcript)
        task_type = _detect_task_type(command_text)
        privacy_level = _detect_privacy_level(command_text)
        speed_priority = _detect_speed_priority(command_text)
        context_size = _detect_context_size(command_text)
        output_format = _detect_output_format(command_text)
        route = self.brain_router.route_task(
            BrainRouteRequest(
                task=command_text,
                task_type=task_type,
                privacy_level=privacy_level,
                speed_priority=speed_priority,
                context_size=context_size,
                output_format=output_format,
            )
        )
        return VoiceCommand(
            transcript=transcript,
            command_text=command_text,
            task_type=task_type,
            privacy_level=privacy_level,
            speed_priority=speed_priority,
            context_size=context_size,
            output_format=output_format,
            brain_routing=route.model_dump(mode="json"),
        )

    async def route_command_to_core(
        self,
        command: VoiceCommand,
        executor: Callable[[SaturnixExecutionRequest], Awaitable[SaturnixExecutionResult]],
    ) -> SaturnixExecutionResult:
        return await executor(
            SaturnixExecutionRequest(
                goal=command.command_text,
                input=f"Voice transcript:\n{command.transcript}",
                task_type=command.task_type,
                privacy_level=command.privacy_level,
                speed_priority=command.speed_priority,
                context_size=command.context_size,
                output_format=command.output_format,
                local_only=command.privacy_level == "local",
                auto_improve=True,
                metadata={"source": "voice", "brain_routing": command.brain_routing},
            )
        )

    async def run_voice_workflow(
        self,
        audio: bytes,
        filename: str,
        executor: Callable[[SaturnixExecutionRequest], Awaitable[SaturnixExecutionResult]],
        synthesize_response: bool = True,
        language: str | None = None,
        stt_prompt: str | None = None,
        tts_voice: str | None = None,
    ) -> VoiceWorkflowResult:
        transcription = await self.speech_to_text(
            audio,
            filename=filename,
            language=language,
            prompt=stt_prompt,
        )
        command = self.extract_command(transcription.text)
        execution = await self.route_command_to_core(command, executor)
        response_text = _response_text_from_execution(execution)
        tts: VoiceSynthesisResult | None = None
        tts_error: str | None = None
        if synthesize_response:
            try:
                tts = await self.text_to_speech(
                    VoiceSynthesisRequest(text=response_text, voice=tts_voice)
                )
            except Exception as exc:
                logger.exception("SATURNIX voice TTS failed.")
                tts_error = str(exc)
        return VoiceWorkflowResult(
            transcription=transcription,
            command=command,
            execution_result=execution,
            response_text=response_text,
            tts=tts,
            tts_error=tts_error,
        )

    async def voice_prompt(self, transcript: str) -> str:
        response = await self.brain_router.complete(
            BrainRequest(
                messages=[
                    BrainMessage(
                        role="system",
                        content=load_prompt("voice.md"),
                    ),
                    BrainMessage(role="user", content=transcript),
                ],
                required_capabilities=[Capability.voice, Capability.reasoning],
            )
        )
        return response.content


def _clean_command_text(transcript: str) -> str:
    text = " ".join(transcript.strip().split())
    prefixes = (
        "saturnix ",
        "hey saturnix ",
        "okay saturnix ",
        "ok saturnix ",
        "please ",
    )
    lowered = text.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _detect_task_type(text: str) -> str:
    lowered = text.lower()
    if _has_any(lowered, {"transcribe", "voice", "speech", "audio", "say aloud", "read aloud"}):
        return "voice"
    if _has_any(lowered, {"code", "coding", "debug", "function", "api", "test", "refactor"}):
        return "coding"
    if _has_any(lowered, {"json", "schema", "function call", "tool call", "automation", "workflow"}):
        return "automation"
    if _has_any(lowered, {"document", "contract", "pdf", "analyze", "deep analysis", "research"}):
        return "deep analysis"
    if _has_any(lowered, {"plan", "architecture", "design", "strategy"}):
        return "architecture"
    return "general"


def _detect_privacy_level(text: str) -> str:
    lowered = text.lower()
    if _has_any(lowered, {"private", "local", "offline", "confidential", "sensitive"}):
        return "local"
    return "standard"


def _detect_speed_priority(text: str) -> str:
    lowered = text.lower()
    if _has_any(lowered, {"urgent", "fast", "quick", "real time", "realtime", "right now"}):
        return "high"
    return "normal"


def _detect_context_size(text: str) -> str:
    lowered = text.lower()
    if _has_any(lowered, {"long document", "large context", "many files", "full repository", "entire repo"}):
        return "large"
    if len(text) > 4000:
        return "large"
    if len(text) > 1000:
        return "medium"
    return "small"


def _detect_output_format(text: str) -> str:
    lowered = text.lower()
    if _has_any(lowered, {"json", "schema"}):
        return "json schema"
    if _has_any(lowered, {"code", "python", "typescript", "javascript"}):
        return "code"
    if _has_any(lowered, {"table", "spreadsheet"}):
        return "table"
    if _has_any(lowered, {"speech", "audio", "voice"}):
        return "voice response"
    return "markdown"


def _response_text_from_execution(execution: SaturnixExecutionResult) -> str:
    output = execution.execution_result.get("output")
    if output:
        return str(output)
    if execution.validation_result.get("findings"):
        return "I ran the command, but validation found issues: " + "; ".join(
            str(finding) for finding in execution.validation_result["findings"][:2]
        )
    return "I ran the SATURNIX workflow, but no output was produced."


def _has_any(text: str, needles: set[str]) -> bool:
    return any(needle in text for needle in needles)
