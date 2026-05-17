from __future__ import annotations

from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.brains.ollama_provider import SaturnixOllamaProvider
from saturnix_harness.core.cognitive_workflow_planner import CognitiveWorkflowPlanner
from saturnix_harness.core.consensus_engine import ConsensusEngine
from saturnix_harness.core.improvement_engine import RecursiveImprovementEngine
from saturnix_harness.config import Settings, get_settings
from saturnix_harness.core.agent_constructor import AgentConstructor
from saturnix_harness.core.execution_engine import ExecutionEngine, SaturnixExecutionEngine
from saturnix_harness.core.intent_mapper import HumanIntentMapper
from saturnix_harness.core.security_sentinel import SecuritySentinel
from saturnix_harness.core.verification_engine import VerificationEngine
from saturnix_harness.core.workflow import NavigationWorkflowBuilder
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.memory.neural_engine import NeuralMemoryEngine
from saturnix_harness.monitoring.events import MonitoringLayer
from saturnix_harness.schemas import (
    AutonomousAgentConstructionRequest,
    CognitiveWorkflowPlanRequest,
    ConsensusRequest,
    ConstructAgentRequest,
    DynamicAgentRequest,
    HarnessRequest,
    HarnessResponse,
    NeuralMemoryCompressionRequest,
    NeuralMemoryRecallRequest,
    NeuralMemoryStoreRequest,
    SaturnixExecutionRequest,
    SaturnixExecutionResult,
    SecurityScanRequest,
)
from saturnix_harness.tools.router import ToolRouter
from saturnix_harness.voice.engine import VoiceEngine


class CoreOrchestrator:
    """Core Orchestrator for the full SATURNIX-HARNESS lifecycle."""

    def __init__(
        self,
        settings: Settings | None = None,
        brain_router: BrainRouter | None = None,
        tool_router: ToolRouter | None = None,
        memory: MemoryManager | None = None,
        monitoring: MonitoringLayer | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.brain_router = brain_router or BrainRouter(self.settings)
        self.ollama_provider = SaturnixOllamaProvider(self.settings)
        self.tool_router = tool_router or ToolRouter()
        self.memory = memory or MemoryManager(self.settings)
        self.neural_memory_engine = NeuralMemoryEngine(self.memory)
        self.monitoring = monitoring or MonitoringLayer()
        self.intent_mapper = HumanIntentMapper()
        self.agent_constructor = AgentConstructor(
            brain_router=self.brain_router,
            tool_router=self.tool_router,
            memory=self.memory,
        )
        self.workflow_builder = NavigationWorkflowBuilder()
        self.cognitive_workflow_planner = CognitiveWorkflowPlanner(
            brain_router=self.brain_router,
            agent_constructor=self.agent_constructor,
            memory=self.memory,
        )
        self.verifier = VerificationEngine(self.brain_router)
        self.consensus_engine = ConsensusEngine(self.brain_router)
        self.security_sentinel = SecuritySentinel()
        self.improvement_engine = RecursiveImprovementEngine(self.memory)
        self.execution_engine = SaturnixExecutionEngine(
            intent_mapper=self.intent_mapper,
            brain_router=self.brain_router,
            agent_constructor=self.agent_constructor,
            workflow_builder=self.workflow_builder,
            verifier=self.verifier,
            tool_router=self.tool_router,
            memory=self.memory,
            monitoring=self.monitoring,
        )
        self.voice_engine = VoiceEngine(self.settings, self.brain_router)

    async def construct_agent(self, request: ConstructAgentRequest):
        spec = self.agent_constructor.construct_for_request(request)
        return spec

    async def construct_agent_blueprint(self, request: DynamicAgentRequest):
        return self.agent_constructor.construct_blueprint(request)

    async def construct_autonomous_agents(
        self,
        request: AutonomousAgentConstructionRequest,
    ):
        return self.agent_constructor.construct_autonomous(request)

    async def execute_goal(self, request: SaturnixExecutionRequest):
        return await self.execution_engine.execute_goal(request)

    async def run_consensus(self, request: ConsensusRequest):
        return await self.consensus_engine.run_consensus(request)

    async def plan_cognitive_workflow(self, request: CognitiveWorkflowPlanRequest):
        return self.cognitive_workflow_planner.plan(request)

    async def scan_security(self, request: SecurityScanRequest):
        return self.security_sentinel.scan(request)

    async def store_neural_memory(self, request: NeuralMemoryStoreRequest):
        return self.neural_memory_engine.store(request)

    async def recall_neural_memory(self, request: NeuralMemoryRecallRequest):
        return self.neural_memory_engine.recall(request)

    async def compress_neural_memory(self, request: NeuralMemoryCompressionRequest):
        return self.neural_memory_engine.compress(request)

    async def analyze_improvement(self, result):
        return self.improvement_engine.analyze_execution(result)

    async def execute_voice(
        self,
        audio: bytes,
        filename: str = "audio.wav",
        synthesize_response: bool = True,
        language: str | None = None,
        stt_prompt: str | None = None,
        tts_voice: str | None = None,
    ):
        return await self.voice_engine.run_voice_workflow(
            audio=audio,
            filename=filename,
            executor=self.execute_goal,
            synthesize_response=synthesize_response,
            language=language,
            stt_prompt=stt_prompt,
            tts_voice=tts_voice,
        )

    async def run(self, request: HarnessRequest) -> HarnessResponse:
        self.monitoring.record(
            name="run.started",
            message="SATURNIX-HARNESS run started.",
            metadata={"goal": request.goal},
        )
        intent = self.intent_mapper.map(request)
        agents = self.agent_constructor.construct_for_intent(
            intent,
            preferred_brain=request.preferred_brain,
        )
        plan = self.workflow_builder.build(intent, agents, input_text=request.input)
        runtimes = self.agent_constructor.runtime_map(agents)
        execution_engine = ExecutionEngine(
            agents=runtimes,
            tool_router=self.tool_router,
            memory=self.memory,
        )
        output, traces = await execution_engine.execute(plan)
        verification = await self.verifier.verify(intent, output)
        if request.auto_improve and not verification.ok:
            improved = await self.verifier.improve(intent, output, verification)
            verification.improved_output = improved
            output = improved
            verification = await self.verifier.verify(intent, output)
            verification.improved_output = improved

        memory_record = self.memory.remember(
            content=output,
            namespace="saturnix:runs",
            kind="harness_response",
            metadata={"goal": request.goal, "verification_score": verification.score},
        )
        synthetic_result = SaturnixExecutionResult(
            goal=request.goal,
            detected_intent=intent.summary,
            agents_used=[agent.name for agent in agents],
            brain_routing={
                "selected_brain": (
                    request.preferred_brain.value if request.preferred_brain else "auto"
                ),
                "fallback_brain": "",
            },
            workflow=[step.model_dump(mode="json") for step in plan.steps],
            execution_result={
                "ok": all(trace.ok for trace in traces),
                "output": output,
                "traces": [trace.model_dump(mode="json") for trace in traces],
            },
            validation_result=verification.model_dump(mode="json"),
            memory_saved=memory_record.model_dump(mode="json"),
            next_actions=[],
        )
        improvement = self.improvement_engine.analyze_execution(synthetic_result)
        self.monitoring.record(
            name="run.completed",
            message="SATURNIX-HARNESS run completed.",
            metadata={"goal": request.goal, "verification_score": verification.score},
        )
        return HarnessResponse(
            goal=request.goal,
            output=output,
            intent=intent,
            plan=plan,
            verification=verification,
            traces=traces,
            metadata={
                "recursive_improvement": improvement.model_dump(mode="json"),
                "recursive_improvement_strategy_ids": improvement.stored_strategy_ids,
            },
        )
