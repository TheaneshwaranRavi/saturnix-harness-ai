from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.monitoring.events import MonitoringLayer
from saturnix_harness.schemas import (
    MemoryRecord,
    MemoryType,
    SaturnixExecutionRequest,
    SaturnixExecutionResult,
    SaveMemoryRequest,
    SearchMemoryRequest,
    UpdateMemoryRequest,
    VoiceCognitiveTurnRequest,
    VoiceCognitiveTurnResult,
    VoiceCommand,
    VoiceRiskAssessment,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
)
from saturnix_harness.voice.engine import VoiceEngine

logger = logging.getLogger(__name__)


class VoiceCognitiveAgent:
    """Realtime-oriented voice control layer for SATURNIX.

    The cognitive agent sits above the raw voice engine. It owns multi-turn
    session state, memory recall, interruption handling, risky action
    confirmation, execution dispatch, and response persistence.
    """

    def __init__(
        self,
        voice_engine: VoiceEngine,
        memory: MemoryManager,
        monitoring: MonitoringLayer,
    ) -> None:
        self.voice_engine = voice_engine
        self.memory = memory
        self.monitoring = monitoring

    async def run_turn(
        self,
        request: VoiceCognitiveTurnRequest,
        executor: Callable[[SaturnixExecutionRequest], Awaitable[SaturnixExecutionResult]],
    ) -> VoiceCognitiveTurnResult:
        started = time.perf_counter()
        timings: dict[str, int] = {}
        session_id = request.session_id or str(uuid4())
        turn_id = str(uuid4())
        namespace = _session_namespace(session_id)

        memory_context = self._recall_context(request, namespace, timings)
        pending = self._pending_confirmation(request, namespace)

        if request.interrupt or _is_interrupt(request.transcript):
            return self._interrupted_result(
                request=request,
                session_id=session_id,
                turn_id=turn_id,
                namespace=namespace,
                pending=pending,
                memory_context=memory_context,
                timings=timings,
                started=started,
            )

        if pending and _is_confirmation_response(request):
            command = VoiceCommand.model_validate(pending.metadata["command"])
            return await self._execute_confirmed_pending(
                request=request,
                session_id=session_id,
                turn_id=turn_id,
                namespace=namespace,
                pending=pending,
                command=command,
                memory_context=memory_context,
                timings=timings,
                started=started,
                executor=executor,
            )

        if pending and _is_rejection(request.transcript):
            return self._cancel_pending_result(
                request=request,
                session_id=session_id,
                turn_id=turn_id,
                namespace=namespace,
                pending=pending,
                memory_context=memory_context,
                timings=timings,
                started=started,
            )

        command_start = time.perf_counter()
        command = self.voice_engine.extract_command(request.transcript)
        timings["intent_analysis_ms"] = _elapsed_ms(command_start)
        risk = _assess_risk(command)

        if risk.requires_confirmation and not request.confirmed:
            token = str(uuid4())
            pending_id = self._save_pending_confirmation(
                namespace=namespace,
                token=token,
                command=command,
                risk=risk,
                request=request,
                turn_id=turn_id,
            )
            response_text = _confirmation_prompt(command, risk, token)
            saved = self._persist_turn(
                request=request,
                session_id=session_id,
                turn_id=turn_id,
                namespace=namespace,
                command=command,
                risk=risk,
                response_text=response_text,
                execution=None,
                pending_record_id=pending_id,
            )
            timings["total_ms"] = _elapsed_ms(started)
            return VoiceCognitiveTurnResult(
                session_id=session_id,
                turn_id=turn_id,
                transcript=request.transcript,
                command=command,
                intent_analysis=_intent_analysis(command),
                brain_routing=command.brain_routing,
                memory_context=memory_context,
                risk_assessment=risk,
                confirmation_required=True,
                confirmation_token=token,
                confirmation_prompt=response_text,
                response_text=response_text,
                stage_timings_ms=timings,
                memory_saved=saved,
            )

        return await self._execute_command(
            request=request,
            session_id=session_id,
            turn_id=turn_id,
            namespace=namespace,
            command=command,
            risk=risk,
            memory_context=memory_context,
            timings=timings,
            started=started,
            executor=executor,
            confirmed=request.confirmed,
        )

    async def run_audio_turn(
        self,
        audio: bytes,
        filename: str,
        executor: Callable[[SaturnixExecutionRequest], Awaitable[SaturnixExecutionResult]],
        session_id: str | None = None,
        user_id: str | None = None,
        synthesize_response: bool = False,
        language: str | None = None,
        stt_prompt: str | None = None,
        tts_voice: str | None = None,
        low_latency_mode: bool = True,
    ) -> VoiceCognitiveTurnResult:
        transcription_started = time.perf_counter()
        transcription = await self.voice_engine.speech_to_text(
            audio,
            filename=filename,
            language=language,
            prompt=stt_prompt,
        )
        request = VoiceCognitiveTurnRequest(
            transcript=transcription.text,
            session_id=session_id,
            user_id=user_id,
            synthesize_response=synthesize_response,
            low_latency_mode=low_latency_mode,
            metadata={"filename": filename, "tts_voice": tts_voice},
        )
        result = await self.run_turn(request, executor)
        result.stage_timings_ms["speech_to_text_ms"] = _elapsed_ms(transcription_started)
        return result

    def _recall_context(
        self,
        request: VoiceCognitiveTurnRequest,
        namespace: str,
        timings: dict[str, int],
    ) -> list[MemoryRecord]:
        if request.memory_limit <= 0:
            timings["memory_recall_ms"] = 0
            return []
        started = time.perf_counter()
        limit = min(request.memory_limit, 3) if request.low_latency_mode else request.memory_limit
        records = self.memory.search_memory(
            SearchMemoryRequest(
                query=request.transcript,
                namespace=namespace,
                memory_type=MemoryType.agent_execution_logs,
                limit=limit,
                include_vector=False,
            )
        )
        if not records:
            records = self.memory.list(namespace=namespace, limit=limit)
            records = [
                record
                for record in records
                if record.memory_type == MemoryType.agent_execution_logs
            ][:limit]
        timings["memory_recall_ms"] = _elapsed_ms(started)
        return records

    def _pending_confirmation(
        self,
        request: VoiceCognitiveTurnRequest,
        namespace: str,
    ) -> MemoryRecord | None:
        query = request.confirmation_token or "pending confirmation"
        pending = self.memory.search_memory(
            SearchMemoryRequest(
                query=query,
                namespace=namespace,
                memory_type=MemoryType.agent_execution_logs,
                tags=["voice_pending"],
                limit=5,
                include_vector=False,
            )
        )
        for record in pending:
            status = record.metadata.get("status")
            token = record.metadata.get("confirmation_token")
            token_matches = not request.confirmation_token or token == request.confirmation_token
            if status == "pending" and token_matches:
                return record
        return None

    async def _execute_confirmed_pending(
        self,
        request: VoiceCognitiveTurnRequest,
        session_id: str,
        turn_id: str,
        namespace: str,
        pending: MemoryRecord,
        command: VoiceCommand,
        memory_context: list[MemoryRecord],
        timings: dict[str, int],
        started: float,
        executor: Callable[[SaturnixExecutionRequest], Awaitable[SaturnixExecutionResult]],
    ) -> VoiceCognitiveTurnResult:
        risk = VoiceRiskAssessment.model_validate(pending.metadata["risk_assessment"])
        result = await self._execute_command(
            request=request,
            session_id=session_id,
            turn_id=turn_id,
            namespace=namespace,
            command=command,
            risk=risk,
            memory_context=memory_context,
            timings=timings,
            started=started,
            executor=executor,
            confirmed=True,
        )
        self._mark_pending(pending, "executed")
        result.memory_saved["confirmed_pending_record_id"] = pending.id
        return result

    async def _execute_command(
        self,
        request: VoiceCognitiveTurnRequest,
        session_id: str,
        turn_id: str,
        namespace: str,
        command: VoiceCommand,
        risk: VoiceRiskAssessment,
        memory_context: list[MemoryRecord],
        timings: dict[str, int],
        started: float,
        executor: Callable[[SaturnixExecutionRequest], Awaitable[SaturnixExecutionResult]],
        confirmed: bool,
    ) -> VoiceCognitiveTurnResult:
        execution_started = time.perf_counter()
        execution = await self.voice_engine.route_command_to_core(
            _command_with_context(command, memory_context, confirmed),
            executor,
        )
        timings["workflow_execution_ms"] = _elapsed_ms(execution_started)
        response_text = _response_text_from_execution(execution)
        tts, tts_error = await self._maybe_synthesize(request, response_text, timings)
        saved = self._persist_turn(
            request=request,
            session_id=session_id,
            turn_id=turn_id,
            namespace=namespace,
            command=command,
            risk=risk,
            response_text=response_text,
            execution=execution,
            pending_record_id=None,
        )
        timings["total_ms"] = _elapsed_ms(started)
        self.monitoring.record(
            name="voice_cognitive.turn_completed",
            message="SATURNIX voice cognitive turn completed.",
            metadata={
                "session_id": session_id,
                "turn_id": turn_id,
                "confirmed": confirmed,
                "risk_level": risk.risk_level,
                "latency_ms": timings["total_ms"],
            },
        )
        return VoiceCognitiveTurnResult(
            session_id=session_id,
            turn_id=turn_id,
            transcript=request.transcript,
            command=command,
            intent_analysis=_intent_analysis(command),
            brain_routing=command.brain_routing,
            memory_context=memory_context,
            risk_assessment=risk,
            execution_result=execution,
            response_text=response_text,
            tts=tts,
            tts_error=tts_error,
            stage_timings_ms=timings,
            memory_saved=saved,
        )

    async def _maybe_synthesize(
        self,
        request: VoiceCognitiveTurnRequest,
        response_text: str,
        timings: dict[str, int],
    ) -> tuple[VoiceSynthesisResult | None, str | None]:
        if not request.synthesize_response:
            return None, None
        started = time.perf_counter()
        try:
            tts = await self.voice_engine.text_to_speech(
                VoiceSynthesisRequest(
                    text=response_text,
                    voice=request.metadata.get("tts_voice"),
                )
            )
            timings["text_to_speech_ms"] = _elapsed_ms(started)
            return tts, None
        except Exception as exc:
            logger.exception("SATURNIX voice cognitive TTS failed.")
            timings["text_to_speech_ms"] = _elapsed_ms(started)
            return None, str(exc)

    def _save_pending_confirmation(
        self,
        namespace: str,
        token: str,
        command: VoiceCommand,
        risk: VoiceRiskAssessment,
        request: VoiceCognitiveTurnRequest,
        turn_id: str,
    ) -> str:
        record = self.memory.save_memory(
            SaveMemoryRequest(
                content=(
                    f"pending confirmation token={token}\n"
                    f"command={command.command_text}\n"
                    f"transcript={request.transcript}"
                ),
                memory_type=MemoryType.agent_execution_logs,
                namespace=namespace,
                kind="voice_pending_confirmation",
                title=f"Pending voice confirmation: {command.command_text[:80]}",
                tags=["voice", "voice_pending", "confirmation_required"],
                metadata={
                    "confirmation_token": token,
                    "command": command.model_dump(mode="json"),
                    "risk_assessment": risk.model_dump(mode="json"),
                    "status": "pending",
                    "turn_id": turn_id,
                    "user_id": request.user_id,
                },
                source="voice_cognitive_agent",
            )
        )
        return record.id

    def _persist_turn(
        self,
        request: VoiceCognitiveTurnRequest,
        session_id: str,
        turn_id: str,
        namespace: str,
        command: VoiceCommand | None,
        risk: VoiceRiskAssessment,
        response_text: str,
        execution: SaturnixExecutionResult | None,
        pending_record_id: str | None,
    ) -> dict[str, str]:
        if not request.persist_context:
            return {}
        user_record = self.memory.save_memory(
            SaveMemoryRequest(
                content=f"user: {request.transcript}",
                memory_type=MemoryType.agent_execution_logs,
                namespace=namespace,
                kind="voice_user_turn",
                title=f"Voice user turn {turn_id}",
                tags=["voice", "conversation", "user_turn"],
                metadata={
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "user_id": request.user_id,
                    "command": command.model_dump(mode="json") if command else None,
                    "risk_assessment": risk.model_dump(mode="json"),
                },
                source="voice_cognitive_agent",
            )
        )
        assistant_record = self.memory.save_memory(
            SaveMemoryRequest(
                content=f"assistant: {response_text}",
                memory_type=MemoryType.agent_execution_logs,
                namespace=namespace,
                kind="voice_assistant_turn",
                title=f"Voice assistant turn {turn_id}",
                tags=["voice", "conversation", "assistant_turn"],
                metadata={
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "execution_ok": (
                        execution.execution_result.get("ok") if execution else None
                    ),
                    "pending_record_id": pending_record_id,
                },
                source="voice_cognitive_agent",
            )
        )
        saved = {
            "namespace": namespace,
            "user_turn_record_id": user_record.id,
            "assistant_turn_record_id": assistant_record.id,
        }
        if pending_record_id:
            saved["pending_confirmation_record_id"] = pending_record_id
        return saved

    def _interrupted_result(
        self,
        request: VoiceCognitiveTurnRequest,
        session_id: str,
        turn_id: str,
        namespace: str,
        pending: MemoryRecord | None,
        memory_context: list[MemoryRecord],
        timings: dict[str, int],
        started: float,
    ) -> VoiceCognitiveTurnResult:
        if pending:
            self._mark_pending(pending, "interrupted")
        risk = _low_risk("Voice interruption requested; no workflow was executed.")
        response_text = "Voice session interrupted. I stopped before running any workflow."
        saved = self._persist_turn(
            request=request,
            session_id=session_id,
            turn_id=turn_id,
            namespace=namespace,
            command=None,
            risk=risk,
            response_text=response_text,
            execution=None,
            pending_record_id=pending.id if pending else None,
        )
        timings["total_ms"] = _elapsed_ms(started)
        return VoiceCognitiveTurnResult(
            session_id=session_id,
            turn_id=turn_id,
            transcript=request.transcript,
            memory_context=memory_context,
            risk_assessment=risk,
            interrupted=True,
            response_text=response_text,
            stage_timings_ms=timings,
            memory_saved=saved,
        )

    def _cancel_pending_result(
        self,
        request: VoiceCognitiveTurnRequest,
        session_id: str,
        turn_id: str,
        namespace: str,
        pending: MemoryRecord,
        memory_context: list[MemoryRecord],
        timings: dict[str, int],
        started: float,
    ) -> VoiceCognitiveTurnResult:
        self._mark_pending(pending, "cancelled")
        risk = _low_risk("Pending risky command was cancelled by user response.")
        response_text = "Cancelled the pending voice command. No workflow was executed."
        saved = self._persist_turn(
            request=request,
            session_id=session_id,
            turn_id=turn_id,
            namespace=namespace,
            command=None,
            risk=risk,
            response_text=response_text,
            execution=None,
            pending_record_id=pending.id,
        )
        timings["total_ms"] = _elapsed_ms(started)
        return VoiceCognitiveTurnResult(
            session_id=session_id,
            turn_id=turn_id,
            transcript=request.transcript,
            memory_context=memory_context,
            risk_assessment=risk,
            response_text=response_text,
            stage_timings_ms=timings,
            memory_saved=saved,
        )

    def _mark_pending(self, pending: MemoryRecord, status: str) -> None:
        metadata = dict(pending.metadata)
        metadata["status"] = status
        self.memory.update_memory(
            pending.id,
            UpdateMemoryRequest(
                content=f"{status} confirmation\n{pending.content}",
                metadata=metadata,
                tags=[*pending.tags, status],
            ),
        )


def _session_namespace(session_id: str) -> str:
    return f"saturnix:voice:{session_id}"


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


def _command_with_context(
    command: VoiceCommand,
    memory_context: list[MemoryRecord],
    confirmed: bool,
) -> VoiceCommand:
    context = "\n".join(record.content for record in memory_context[:5])
    if not context and not confirmed:
        return command
    suffix = []
    if confirmed:
        suffix.append("Risky action was explicitly confirmed by the user.")
    if context:
        suffix.append(f"Relevant voice memory context:\n{context}")
    updated = command.model_copy()
    updated.transcript = f"{command.transcript}\n\n" + "\n\n".join(suffix)
    return updated


def _assess_risk(command: VoiceCommand) -> VoiceRiskAssessment:
    text = f"{command.command_text} {command.transcript}".lower()
    risky_terms = sorted(term for term in _RISKY_TERMS if term in text)
    critical_terms = sorted(term for term in _CRITICAL_TERMS if term in text)
    blocked = []
    if any(term in text for term in _SECRET_TERMS):
        blocked.append("Do not expose or read secrets without explicit approved scope.")
    if critical_terms:
        return VoiceRiskAssessment(
            risk_level="critical",
            requires_confirmation=True,
            risky_terms=[*critical_terms, *risky_terms],
            reason=(
                "Command may affect production, secrets, money, external messaging, "
                "or destructive state."
            ),
            blocked_actions=blocked,
        )
    if risky_terms:
        return VoiceRiskAssessment(
            risk_level="high",
            requires_confirmation=True,
            risky_terms=risky_terms,
            reason="Command includes side-effectful or destructive action terms.",
            blocked_actions=blocked,
        )
    if command.privacy_level == "local":
        return VoiceRiskAssessment(
            risk_level="medium",
            requires_confirmation=False,
            risky_terms=[],
            reason="Private/local command should keep context on controlled execution paths.",
            blocked_actions=blocked,
        )
    return _low_risk("No risky voice-control terms were detected.")


def _low_risk(reason: str) -> VoiceRiskAssessment:
    return VoiceRiskAssessment(
        risk_level="low",
        requires_confirmation=False,
        risky_terms=[],
        reason=reason,
        blocked_actions=[],
    )


def _confirmation_prompt(command: VoiceCommand, risk: VoiceRiskAssessment, token: str) -> str:
    terms = ", ".join(risk.risky_terms[:6]) or "side effects"
    return (
        "This voice command needs confirmation before execution: "
        f"'{command.command_text}'. Risk level: {risk.risk_level}; terms: {terms}. "
        f"Reply with yes and confirmation token {token} to proceed, or say cancel."
    )


def _intent_analysis(command: VoiceCommand) -> dict[str, str]:
    return {
        "command_text": command.command_text,
        "task_type": command.task_type,
        "privacy_level": command.privacy_level,
        "speed_priority": command.speed_priority,
        "context_size": command.context_size,
        "output_format": command.output_format,
    }


def _response_text_from_execution(execution: SaturnixExecutionResult) -> str:
    output = execution.execution_result.get("output")
    if output:
        return str(output)
    findings = execution.validation_result.get("findings", [])
    if findings:
        return "I ran the workflow, but validation found issues: " + "; ".join(
            str(finding) for finding in findings[:2]
        )
    return "I ran the SATURNIX workflow, but no output was produced."


def _is_interrupt(transcript: str) -> bool:
    text = transcript.strip().lower()
    return text in _INTERRUPT_PHRASES or any(
        text.startswith(prefix) for prefix in _INTERRUPT_PREFIXES
    )


def _is_confirmation_response(request: VoiceCognitiveTurnRequest) -> bool:
    return request.confirmed or _is_affirmation(request.transcript)


def _is_affirmation(transcript: str) -> bool:
    text = transcript.strip().lower()
    return text in _AFFIRMATIONS or text.startswith(("yes ", "confirm ", "proceed "))


def _is_rejection(transcript: str) -> bool:
    text = transcript.strip().lower()
    return text in _REJECTIONS or text.startswith(("no ", "cancel ", "stop "))


_RISKY_TERMS = {
    "commit",
    "delete",
    "deploy",
    "drop",
    "email",
    "merge",
    "overwrite",
    "publish",
    "push",
    "remove",
    "restart",
    "send",
    "shutdown",
    "transfer",
    "wipe",
}

_CRITICAL_TERMS = {
    "api key",
    "buy",
    "customer data",
    "payment",
    "private key",
    "production",
    "purchase",
    "secret",
    "token",
}

_SECRET_TERMS = {
    ".env",
    "api key",
    "password",
    "private key",
    "secret",
    "token",
}

_INTERRUPT_PHRASES = {
    "abort",
    "cancel",
    "interrupt",
    "never mind",
    "stop",
    "stop saturnix",
}

_INTERRUPT_PREFIXES = (
    "cancel this",
    "stop this",
    "interrupt this",
    "abort this",
)

_AFFIRMATIONS = {
    "confirm",
    "confirmed",
    "do it",
    "go ahead",
    "proceed",
    "yes",
    "yes proceed",
}

_REJECTIONS = {
    "cancel",
    "do not",
    "no",
    "no cancel",
    "stop",
}
