from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Capability(str, Enum):
    reasoning = "reasoning"
    coding = "coding"
    planning = "planning"
    orchestration = "orchestration"
    long_context = "long_context"
    document_understanding = "document_understanding"
    structured_output = "structured_output"
    function_calling = "function_calling"
    local_private = "local_private"
    voice = "voice"
    realtime_speech = "realtime_speech"
    verification = "verification"


class BrainName(str, Enum):
    openai = "openai"
    claude = "claude"
    gemini = "gemini"
    ollama_gemma = "ollama_gemma"
    ollama_coding = "ollama_coding"
    groq = "groq"
    mock = "mock"


class MemoryType(str, Enum):
    user_preferences = "user_preferences"
    project_history = "project_history"
    agent_execution_logs = "agent_execution_logs"
    successful_workflows = "successful_workflows"
    failed_workflows = "failed_workflows"
    reusable_prompts = "reusable_prompts"
    code_snippets = "code_snippets"
    vector_memory = "vector_memory"


class BrainMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: str


class BrainRequest(BaseModel):
    messages: list[BrainMessage]
    required_capabilities: list[Capability] = Field(default_factory=list)
    preferred_brain: BrainName | None = None
    local_only: bool = False
    temperature: float = 0.2
    max_tokens: int | None = None
    response_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BrainResponse(BaseModel):
    provider: BrainName
    model: str
    content: str
    raw: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int | None = None
    usage: dict[str, Any] = Field(default_factory=dict)


class OllamaGenerationResult(BaseModel):
    ok: bool
    model: str
    output: str
    raw: dict[str, Any] = Field(default_factory=dict)
    fallback_used: bool = False
    error: str | None = None


class OllamaHealthResult(BaseModel):
    enabled: bool
    running: bool
    base_url: str
    available_models: list[str] = Field(default_factory=list)
    supported_models: dict[str, str] = Field(default_factory=dict)
    missing_supported_models: dict[str, str] = Field(default_factory=dict)
    detail: str | None = None


class OllamaTaskClassification(BaseModel):
    task_type: str
    privacy_level: str
    speed_priority: str
    context_size: str
    output_format: str
    local_model: str
    reason: str


class OllamaGenerateRequest(BaseModel):
    prompt: str
    model: str | None = None
    system: str | None = None
    temperature: float = 0.2
    max_tokens: int | None = None
    fallback_text: str | None = None


class OllamaCodeGenerateRequest(BaseModel):
    prompt: str
    model: str | None = None
    language: str | None = None
    temperature: float = 0.1
    max_tokens: int | None = None
    fallback_text: str | None = None


class OllamaSummarizeRequest(BaseModel):
    text: str
    model: str | None = "gemma"
    max_tokens: int | None = 512
    fallback_text: str | None = None


class OllamaClassifyRequest(BaseModel):
    task: str


class ProviderHealth(BaseModel):
    name: BrainName
    model: str
    enabled: bool
    available: bool
    capabilities: list[Capability]
    detail: str | None = None


class RoutingDecision(BaseModel):
    selected: BrainName
    model: str
    reason: str
    fallback_chain: list[BrainName] = Field(default_factory=list)


class BrainRouteRequest(BaseModel):
    task: str = ""
    task_type: str = ""
    privacy_level: str = ""
    speed_priority: str = ""
    context_size: str = ""
    output_format: str = ""


class BrainRouteResponse(BaseModel):
    selected_brain: str
    reason: str
    fallback_brain: str
    execution_strategy: str


class ConsensusRequest(BaseModel):
    task: str
    context: str | None = None
    task_type: str = "reasoning"
    privacy_level: str = "standard"
    output_format: str = "markdown"
    min_brains: int = Field(default=2, ge=1, le=5)
    max_brains: int = Field(default=4, ge=1, le=5)
    include_local: bool = True
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_tokens: int | None = None


class BrainComparison(BaseModel):
    brain: str
    model: str
    ok: bool
    output: str = ""
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    key_claims: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    error: str | None = None


class ConsensusResult(BaseModel):
    consensus_result: str
    brain_comparisons: list[BrainComparison]
    confidence_score: float = Field(ge=0.0, le=1.0)
    detected_conflicts: list[str]
    final_reasoning: str


class CognitiveWorkflowPlanRequest(BaseModel):
    goal: str
    context: str | None = None
    task_type: str = ""
    privacy_level: str = "standard"
    speed_priority: str = "normal"
    output_format: str = "markdown"
    constraints: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    max_parallelism: int = Field(default=3, ge=1, le=12)
    persist_plan: bool = True


class WorkflowTreeNode(BaseModel):
    id: str
    name: str
    purpose: str
    agent: str
    brain: str
    complexity: str
    children: list["WorkflowTreeNode"] = Field(default_factory=list)


class WorkflowGraphNode(BaseModel):
    id: str
    name: str
    description: str
    depends_on: list[str] = Field(default_factory=list)
    priority: int = Field(ge=1, le=5)
    complexity: str
    assigned_agent: str
    assigned_brain: str
    estimated_cost: str
    estimated_runtime_seconds: int


class WorkflowGraphEdge(BaseModel):
    source: str
    target: str
    reason: str


class CognitiveWorkflowPlanResult(BaseModel):
    workflow_tree: WorkflowTreeNode
    execution_graph: dict[str, list[dict[str, Any]]]
    critical_path: list[str]
    parallel_execution_opportunities: list[list[str]]
    estimated_execution_cost: str
    estimated_runtime: str
    estimated_runtime_seconds: int
    memory_saved: dict[str, Any] = Field(default_factory=dict)


class SecurityScanRequest(BaseModel):
    prompt: str | None = None
    task: str | None = None
    workflow: list[dict[str, Any]] = Field(default_factory=list)
    code: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    container_config: str | None = None
    file_paths: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    external_inputs: dict[str, Any] = Field(default_factory=dict)
    sensitivity_level: str = "standard"


class SecurityScanResult(BaseModel):
    security_score: str
    risks_detected: list[str] = Field(default_factory=list)
    recommended_fixes: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    name: str
    ok: bool
    output: Any = None
    error: str | None = None


class AgentSpec(BaseModel):
    name: str
    role: str
    mission: str
    system_prompt: str
    required_capabilities: list[Capability] = Field(default_factory=list)
    preferred_brain: BrainName | None = None
    tools: list[str] = Field(default_factory=list)
    memory_namespace: str = "default"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConstructAgentRequest(BaseModel):
    goal: str
    requested_name: str | None = None
    required_capabilities: list[Capability] = Field(default_factory=list)
    preferred_brain: BrainName | None = None
    local_only: bool = False
    tools: list[str] = Field(default_factory=list)


class AgentInputDefinition(BaseModel):
    name: str
    description: str
    required: bool = True
    data_type: str = "string"


class AgentWorkflowStepDefinition(BaseModel):
    order: int = Field(ge=1)
    name: str
    description: str
    expected_output: str


class AgentValidationRule(BaseModel):
    name: str
    description: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"


class AgentMemoryRules(BaseModel):
    namespace: str
    recall_policy: str
    write_policy: str
    retention_policy: str = "retain useful execution summaries and user-approved facts"


class AgentFailureHandling(BaseModel):
    max_retries: int = Field(default=2, ge=0, le=10)
    retry_strategy: str = "retry with clarified context and reduced scope"
    fallback_brain: str
    escalation_policy: str = (
        "return a structured failure report with missing inputs and next actions"
    )


class SaturnixAgentBlueprint(BaseModel):
    agent_name: str
    purpose: str
    best_brain: str
    inputs: list[AgentInputDefinition]
    tools: list[str]
    workflow_steps: list[AgentWorkflowStepDefinition]
    output_format: str
    validation_rules: list[AgentValidationRule]
    memory_rules: AgentMemoryRules
    failure_handling: AgentFailureHandling


class DynamicAgentRequest(BaseModel):
    task: str
    agent_name: str | None = None
    purpose: str | None = None
    task_type: str = ""
    privacy_level: str = "standard"
    speed_priority: str = "normal"
    context_size: str = "medium"
    output_format: str = "markdown"
    inputs: list[AgentInputDefinition] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    validation_rules: list[AgentValidationRule] = Field(default_factory=list)
    memory_namespace: str | None = None


class AutonomousAgentConstructionRequest(BaseModel):
    task: str
    task_type: str = ""
    privacy_level: str = "standard"
    speed_priority: str = "normal"
    context_size: str = "medium"
    output_format: str = "markdown"
    required_tools: list[str] = Field(default_factory=list)
    security_requirements: list[str] = Field(default_factory=list)
    memory_needs: list[str] = Field(default_factory=list)
    execution_cost: str = "balanced"
    max_agents: int = Field(default=5, ge=1, le=12)
    allow_new_agents: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class AutonomousAgentDefinition(BaseModel):
    agent_name: str
    purpose: str
    best_brain: str
    required_tools: list[str]
    workflow: list[str]
    validation_rules: list[str]
    memory_rules: list[str]
    fallback_logic: list[str]


class AutonomousAgentConstructionResult(BaseModel):
    task_complexity: str
    required_expertise: list[str]
    required_tools: list[str]
    security_requirements: list[str]
    execution_cost: str
    memory_needs: list[str]
    reused_agents: list[AutonomousAgentDefinition] = Field(default_factory=list)
    created_agents: list[AutonomousAgentDefinition] = Field(default_factory=list)
    duplicate_agents_avoided: list[str] = Field(default_factory=list)
    coordination_workflow: list[str] = Field(default_factory=list)
    scalability_notes: list[str] = Field(default_factory=list)
    memory_saved: dict[str, Any] = Field(default_factory=dict)


class IntentMap(BaseModel):
    original_goal: str
    summary: str
    domain: str = "general"
    expected_outputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    required_capabilities: list[Capability] = Field(default_factory=list)
    local_only: bool = False


class WorkflowStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    agent_name: str | None = None
    action: Literal["brain", "tool", "memory_write", "memory_search"] = "brain"
    prompt: str | None = None
    tool_call: ToolCall | None = None
    required_capabilities: list[Capability] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    goal: str
    steps: list[WorkflowStep]
    agents: list[AgentSpec] = Field(default_factory=list)


class ExecutionTrace(BaseModel):
    step_id: str
    step_name: str
    ok: bool
    output: Any = None
    error: str | None = None
    provider: BrainName | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class VerificationResult(BaseModel):
    ok: bool
    score: float = Field(ge=0.0, le=1.0)
    findings: list[str] = Field(default_factory=list)
    improved_output: str | None = None


class HarnessRequest(BaseModel):
    goal: str
    input: str | None = None
    required_capabilities: list[Capability] = Field(default_factory=list)
    preferred_brain: BrainName | None = None
    local_only: bool = False
    auto_improve: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class HarnessResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str = Field(default_factory=lambda: str(uuid4()))
    goal: str
    output: str
    intent: IntentMap
    plan: WorkflowPlan
    verification: VerificationResult
    traces: list[ExecutionTrace] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SaturnixExecutionRequest(BaseModel):
    goal: str
    input: str | None = None
    task_type: str = ""
    privacy_level: str = "standard"
    speed_priority: str = "normal"
    context_size: str = "medium"
    output_format: str = "markdown"
    local_only: bool = False
    auto_improve: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class SaturnixExecutionResult(BaseModel):
    goal: str
    detected_intent: str
    agents_used: list[str]
    brain_routing: dict[str, Any]
    workflow: list[dict[str, Any]]
    execution_result: dict[str, Any]
    validation_result: dict[str, Any]
    memory_saved: dict[str, Any]
    next_actions: list[str]


class RecursiveImprovementReport(BaseModel):
    optimization_report: list[str] = Field(default_factory=list)
    architecture_improvements: list[str] = Field(default_factory=list)
    prompt_upgrades: list[str] = Field(default_factory=list)
    routing_improvements: list[str] = Field(default_factory=list)
    execution_improvements: list[str] = Field(default_factory=list)
    memory_improvements: list[str] = Field(default_factory=list)
    agent_coordination_improvements: list[str] = Field(default_factory=list)
    detected_failures: list[str] = Field(default_factory=list)
    detected_bottlenecks: list[str] = Field(default_factory=list)
    detected_hallucinations: list[str] = Field(default_factory=list)
    detected_wasted_tokens: list[str] = Field(default_factory=list)
    detected_weak_workflows: list[str] = Field(default_factory=list)
    detected_repeated_mistakes: list[str] = Field(default_factory=list)
    stored_strategy_ids: list[str] = Field(default_factory=list)


class VoiceTranscriptionResult(BaseModel):
    text: str
    model: str
    filename: str
    language: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class VoiceSynthesisRequest(BaseModel):
    text: str
    model: str | None = None
    voice: str | None = None
    response_format: str | None = None


class VoiceSynthesisResult(BaseModel):
    text: str
    model: str
    voice: str
    response_format: str
    content_type: str
    audio_base64: str


class VoiceCommandRequest(BaseModel):
    transcript: str


class VoiceCommand(BaseModel):
    transcript: str
    command_text: str
    task_type: str
    privacy_level: str
    speed_priority: str
    context_size: str
    output_format: str
    brain_routing: dict[str, Any]


class VoiceWorkflowResult(BaseModel):
    transcription: VoiceTranscriptionResult
    command: VoiceCommand
    execution_result: SaturnixExecutionResult
    response_text: str
    tts: VoiceSynthesisResult | None = None
    tts_error: str | None = None


class MemoryRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    namespace: str = "default"
    memory_type: MemoryType = MemoryType.vector_memory
    kind: str = "note"
    title: str | None = None
    content: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SaveMemoryRequest(BaseModel):
    content: str
    memory_type: MemoryType = MemoryType.vector_memory
    namespace: str = "default"
    kind: str = "note"
    title: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None


class SearchMemoryRequest(BaseModel):
    query: str = ""
    namespace: str | None = None
    memory_type: MemoryType | None = None
    tags: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=100)
    include_vector: bool = True


class UpdateMemoryRequest(BaseModel):
    content: str | None = None
    memory_type: MemoryType | None = None
    namespace: str | None = None
    kind: str | None = None
    title: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    source: str | None = None


class DeleteMemoryResult(BaseModel):
    id: str
    deleted: bool


class MemorySummary(BaseModel):
    namespace: str | None = None
    memory_type: MemoryType | None = None
    total_records: int
    type_counts: dict[str, int]
    recent_records: list[MemoryRecord]
    summary: str


class NeuralMemoryStoreRequest(BaseModel):
    content: str
    category: Literal[
        "successful_workflow",
        "failed_workflow",
        "user_preference",
        "project_architecture",
        "reasoning_pattern",
        "optimization_strategy",
        "code_snippet",
        "reusable_agent_structure",
    ] = "reasoning_pattern"
    namespace: str = "saturnix:neural"
    title: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    importance_score: float = Field(default=0.6, ge=0.0, le=1.0)
    source: str | None = "neural_memory_engine"
    link_query: str | None = None
    compress: bool = True


class NeuralMemoryLink(BaseModel):
    source_id: str
    target_id: str
    relationship: str
    strength: float = Field(ge=0.0, le=1.0)
    reason: str


class NeuralMemoryStoreResult(BaseModel):
    memory: MemoryRecord
    compressed_summary: str
    linked_memory_ids: list[str] = Field(default_factory=list)
    aging_policy: dict[str, Any] = Field(default_factory=dict)


class NeuralMemoryRecallRequest(BaseModel):
    query: str
    namespace: str = "saturnix:neural"
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    limit: int = Field(default=8, ge=1, le=50)
    include_links: bool = True
    include_summary: bool = True
    half_life_days: int = Field(default=180, ge=1, le=3650)


class NeuralMemoryHit(BaseModel):
    memory: MemoryRecord
    rank_score: float = Field(ge=0.0, le=1.0)
    semantic_score: float = Field(ge=0.0, le=1.0)
    importance_score: float = Field(ge=0.0, le=1.0)
    recency_score: float = Field(ge=0.0, le=1.0)
    age_days: float = Field(ge=0.0)
    linked_memory_ids: list[str] = Field(default_factory=list)


class NeuralMemoryRecallResult(BaseModel):
    query: str
    ranked_memories: list[NeuralMemoryHit]
    context_summary: str
    compressed_context: str
    memory_links: list[NeuralMemoryLink] = Field(default_factory=list)
    aging_notes: list[str] = Field(default_factory=list)


class NeuralMemoryCompressionRequest(BaseModel):
    namespace: str = "saturnix:neural"
    category: str | None = None
    limit: int = Field(default=50, ge=1, le=500)
    title: str | None = None


class NeuralMemoryCompressionResult(BaseModel):
    summary_record: MemoryRecord
    source_record_ids: list[str]
    compression_ratio: float
    summary: str


class RuntimeEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    level: Literal["debug", "info", "warning", "error"] = "info"
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
