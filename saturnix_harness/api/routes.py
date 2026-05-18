from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from saturnix_harness.api.dependencies import get_orchestrator
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.schemas import (
    AutonomousAgentConstructionRequest,
    BrainRouteRequest,
    CognitiveWorkflowPlanRequest,
    ConsensusRequest,
    ConstructAgentRequest,
    DynamicAgentRequest,
    ForgeBuildRequest,
    HarnessRequest,
    MemoryRecord,
    MemoryType,
    NeuralMemoryCompressionRequest,
    NeuralMemoryRecallRequest,
    NeuralMemoryStoreRequest,
    OllamaClassifyRequest,
    OllamaCodeGenerateRequest,
    OllamaGenerateRequest,
    OllamaSummarizeRequest,
    SaveMemoryRequest,
    SearchMemoryRequest,
    SaturnixExecutionRequest,
    SaturnixExecutionResult,
    SecurityScanRequest,
    ToolRoutingRequest,
    UpdateMemoryRequest,
    VoiceCognitiveTurnRequest,
    VoiceCommandRequest,
    VoiceSynthesisRequest,
)
from saturnix_harness.voice.engine import VoiceEngine

router = APIRouter(prefix="/v1")
phase1_router = APIRouter(tags=["Phase 1"])


@phase1_router.get("/health")
async def phase1_health(orchestrator: CoreOrchestrator = Depends(get_orchestrator)):
    return await health(orchestrator)


@phase1_router.post("/execute")
async def phase1_execute(
    request: SaturnixExecutionRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.execute_goal(request)


@phase1_router.get("/agents")
async def phase1_agents(orchestrator: CoreOrchestrator = Depends(get_orchestrator)):
    required_names = {
        "Research Agent",
        "Coding Agent",
        "Automation Agent",
        "Voice Agent",
        "Memory Agent",
        "Verification Agent",
    }
    return [
        agent
        for agent in orchestrator.agent_constructor.list_default_agents()
        if agent.agent_name in required_names
    ]


@phase1_router.get("/brains")
async def phase1_brains(orchestrator: CoreOrchestrator = Depends(get_orchestrator)):
    return await orchestrator.brain_router.health()


@router.get("/health")
async def health(orchestrator: CoreOrchestrator = Depends(get_orchestrator)):
    return {
        "status": "ok",
        "environment": orchestrator.settings.saturnix_env,
        "brains": [health.model_dump() for health in await orchestrator.brain_router.health()],
        "tools": [tool.model_dump() for tool in orchestrator.tool_router.specs()],
    }


@router.get("/brains")
async def list_brains(orchestrator: CoreOrchestrator = Depends(get_orchestrator)):
    return await orchestrator.brain_router.health()


@router.post("/brains/route")
async def route_brain(
    request: BrainRouteRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return orchestrator.brain_router.route_task(request)


@router.post("/consensus/run")
async def run_consensus(
    request: ConsensusRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.run_consensus(request)


@router.post("/workflows/plan")
async def plan_cognitive_workflow(
    request: CognitiveWorkflowPlanRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.plan_cognitive_workflow(request)


@router.post("/security/scan")
async def scan_security(
    request: SecurityScanRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.scan_security(request)


@router.post("/tools/route")
async def route_tools(
    request: ToolRoutingRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.route_tools(request)


@router.post("/forge/build")
async def forge_build(
    request: ForgeBuildRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.forge_build(request)


@router.post("/neural-memory/store")
async def store_neural_memory(
    request: NeuralMemoryStoreRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.store_neural_memory(request)


@router.post("/neural-memory/recall")
async def recall_neural_memory(
    request: NeuralMemoryRecallRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.recall_neural_memory(request)


@router.post("/neural-memory/compress")
async def compress_neural_memory(
    request: NeuralMemoryCompressionRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.compress_neural_memory(request)


@router.get("/ollama/health")
async def ollama_health(orchestrator: CoreOrchestrator = Depends(get_orchestrator)):
    return await orchestrator.ollama_provider.health_check()


@router.post("/ollama/generate")
async def ollama_generate(
    request: OllamaGenerateRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.ollama_provider.generate(
        prompt=request.prompt,
        model=request.model,
        system=request.system,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        fallback_text=request.fallback_text,
    )


@router.post("/ollama/code-generate")
async def ollama_code_generate(
    request: OllamaCodeGenerateRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.ollama_provider.code_generate(
        prompt=request.prompt,
        model=request.model,
        language=request.language,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        fallback_text=request.fallback_text,
    )


@router.post("/ollama/summarize")
async def ollama_summarize(
    request: OllamaSummarizeRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.ollama_provider.summarize(
        text=request.text,
        model=request.model,
        max_tokens=request.max_tokens,
        fallback_text=request.fallback_text,
    )


@router.post("/ollama/classify-task")
async def ollama_classify_task(
    request: OllamaClassifyRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return orchestrator.ollama_provider.classify_task(request.task)


@router.get("/events")
async def list_events(
    limit: int = 50,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return orchestrator.monitoring.recent(limit=limit)


@router.post("/agents/construct")
async def construct_agent(
    request: ConstructAgentRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.construct_agent(request)


@router.get("/agents/defaults")
async def list_default_agents(orchestrator: CoreOrchestrator = Depends(get_orchestrator)):
    return orchestrator.agent_constructor.list_default_agents()


@router.post("/agents/construct-blueprint")
async def construct_agent_blueprint(
    request: DynamicAgentRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.construct_agent_blueprint(request)


@router.post("/agents/autonomous-construct")
async def construct_autonomous_agents(
    request: AutonomousAgentConstructionRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.construct_autonomous_agents(request)


@router.post("/runs")
async def run_harness(
    request: HarnessRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    try:
        return await orchestrator.run(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/execution/run")
async def run_execution_engine(
    request: SaturnixExecutionRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.execute_goal(request)


@router.post("/improvement/analyze")
async def analyze_recursive_improvement(
    result: SaturnixExecutionResult,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return await orchestrator.analyze_improvement(result)


@router.post("/memory")
async def remember(
    record: MemoryRecord,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return orchestrator.memory.save_memory(
        SaveMemoryRequest(
            content=record.content,
            memory_type=record.memory_type,
            namespace=record.namespace,
            kind=record.kind,
            title=record.title,
            tags=record.tags,
            metadata=record.metadata,
            source=record.source,
        )
    )


@router.post("/memory/save")
async def save_memory(
    request: SaveMemoryRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return orchestrator.memory.save_memory(request)


@router.get("/memory/search")
async def search_memory(
    query: str,
    namespace: str | None = "default",
    memory_type: MemoryType | None = None,
    limit: int = 5,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return orchestrator.memory.search_memory(
        SearchMemoryRequest(
            query=query,
            namespace=namespace,
            memory_type=memory_type,
            limit=limit,
        )
    )


@router.post("/memory/search")
async def post_search_memory(
    request: SearchMemoryRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return orchestrator.memory.search_memory(request)


@router.patch("/memory/{record_id}")
async def update_memory(
    record_id: str,
    request: UpdateMemoryRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    record = orchestrator.memory.update_memory(record_id, request)
    if not record:
        raise HTTPException(status_code=404, detail=f"Memory record not found: {record_id}")
    return record


@router.delete("/memory/{record_id}")
async def delete_memory(
    record_id: str,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    result = orchestrator.memory.delete_memory(record_id)
    if not result.deleted:
        raise HTTPException(status_code=404, detail=f"Memory record not found: {record_id}")
    return result


@router.get("/memory/summary")
async def summarize_memory(
    namespace: str | None = None,
    memory_type: MemoryType | None = None,
    limit: int = 20,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return orchestrator.memory.summarize_memory(
        namespace=namespace,
        memory_type=memory_type,
        limit=limit,
    )


@router.post("/voice/transcribe")
async def transcribe_voice(
    file: UploadFile,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    voice_engine = VoiceEngine(orchestrator.settings, orchestrator.brain_router)
    try:
        content = await file.read()
        return await voice_engine.transcribe_bytes(content, filename=file.filename or "audio.wav")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/voice/tts")
async def voice_text_to_speech(
    request: VoiceSynthesisRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    try:
        return await orchestrator.voice_engine.text_to_speech(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/voice/command")
async def extract_voice_command(
    request: VoiceCommandRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    return orchestrator.voice_engine.extract_command(request.transcript)


@router.post("/voice/cognitive/turn")
async def run_voice_cognitive_turn(
    request: VoiceCognitiveTurnRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    try:
        return await orchestrator.execute_voice_cognitive_turn(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/voice/cognitive/run")
async def run_voice_cognitive_audio(
    file: UploadFile,
    session_id: str | None = None,
    user_id: str | None = None,
    synthesize_response: bool = False,
    language: str | None = None,
    stt_prompt: str | None = None,
    tts_voice: str | None = None,
    low_latency_mode: bool = True,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    try:
        content = await file.read()
        return await orchestrator.execute_voice_cognitive_audio(
            audio=content,
            filename=file.filename or "audio.wav",
            session_id=session_id,
            user_id=user_id,
            synthesize_response=synthesize_response,
            language=language,
            stt_prompt=stt_prompt,
            tts_voice=tts_voice,
            low_latency_mode=low_latency_mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/voice/run")
async def run_voice_workflow(
    file: UploadFile,
    synthesize_response: bool = True,
    language: str | None = None,
    stt_prompt: str | None = None,
    tts_voice: str | None = None,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
):
    try:
        content = await file.read()
        return await orchestrator.execute_voice(
            audio=content,
            filename=file.filename or "audio.wav",
            synthesize_response=synthesize_response,
            language=language,
            stt_prompt=stt_prompt,
            tts_voice=tts_voice,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
