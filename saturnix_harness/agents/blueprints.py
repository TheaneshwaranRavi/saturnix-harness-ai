from __future__ import annotations

from saturnix_harness.schemas import (
    AgentFailureHandling,
    AgentInputDefinition,
    AgentMemoryRules,
    AgentValidationRule,
    AgentWorkflowStepDefinition,
    SaturnixAgentBlueprint,
)


def default_agent_blueprints() -> dict[str, SaturnixAgentBlueprint]:
    """Return SATURNIX default agent blueprints keyed by stable agent name."""

    return {
        "research_agent": SaturnixAgentBlueprint(
            agent_name="Research Agent",
            purpose="Gather, compare, and synthesize research from long or complex source material.",
            best_brain="Claude",
            inputs=[
                AgentInputDefinition(name="research_question", description="Primary question to answer."),
                AgentInputDefinition(
                    name="source_material",
                    description="Documents, notes, URLs, or extracted text to analyze.",
                    required=False,
                ),
                AgentInputDefinition(
                    name="constraints",
                    description="Scope, citation, freshness, privacy, or output constraints.",
                    required=False,
                ),
            ],
            tools=["memory_search", "web_search_optional", "document_parser"],
            workflow_steps=[
                AgentWorkflowStepDefinition(
                    order=1,
                    name="Clarify Research Target",
                    description="Identify domain, scope, evidence requirements, and unknowns.",
                    expected_output="Research plan and assumptions.",
                ),
                AgentWorkflowStepDefinition(
                    order=2,
                    name="Analyze Sources",
                    description="Extract claims, evidence, contradictions, and gaps from source material.",
                    expected_output="Evidence table with confidence notes.",
                ),
                AgentWorkflowStepDefinition(
                    order=3,
                    name="Synthesize Answer",
                    description="Produce a concise answer with caveats and next research steps.",
                    expected_output="Research synthesis.",
                ),
            ],
            output_format="markdown report with evidence notes",
            validation_rules=[
                AgentValidationRule(
                    name="source_grounding",
                    description="Claims must be tied to provided or retrieved source material.",
                    severity="high",
                ),
                AgentValidationRule(
                    name="uncertainty_marking",
                    description="Unknowns, assumptions, and weak evidence must be labeled.",
                ),
            ],
            memory_rules=AgentMemoryRules(
                namespace="agent:research",
                recall_policy="retrieve prior research summaries and known user preferences",
                write_policy="store final synthesis, durable facts, and open questions",
            ),
            failure_handling=AgentFailureHandling(fallback_brain="GPT"),
        ),
        "coding_agent": SaturnixAgentBlueprint(
            agent_name="Coding Agent",
            purpose="Design, implement, debug, and verify software changes.",
            best_brain="GPT",
            inputs=[
                AgentInputDefinition(name="task", description="Coding task or bug to solve."),
                AgentInputDefinition(name="code_context", description="Relevant files, errors, or APIs."),
                AgentInputDefinition(
                    name="acceptance_criteria",
                    description="Behavior, tests, or performance requirements.",
                    required=False,
                ),
            ],
            tools=["code_search", "test_runner", "safe_calculator"],
            workflow_steps=[
                AgentWorkflowStepDefinition(
                    order=1,
                    name="Inspect Context",
                    description="Read relevant code, tests, and project conventions.",
                    expected_output="Implementation notes and risk list.",
                ),
                AgentWorkflowStepDefinition(
                    order=2,
                    name="Implement",
                    description="Make focused changes using existing patterns.",
                    expected_output="Patch or code output.",
                ),
                AgentWorkflowStepDefinition(
                    order=3,
                    name="Verify",
                    description="Run targeted checks and summarize residual risk.",
                    expected_output="Verification result.",
                ),
            ],
            output_format="code patch plus verification summary",
            validation_rules=[
                AgentValidationRule(
                    name="tests_or_reason",
                    description="Run relevant tests or explain why they could not be run.",
                    severity="high",
                ),
                AgentValidationRule(
                    name="scope_control",
                    description="Avoid unrelated refactors and generated churn.",
                    severity="medium",
                ),
            ],
            memory_rules=AgentMemoryRules(
                namespace="agent:coding",
                recall_policy="retrieve project conventions, previous decisions, and known failures",
                write_policy="store implementation summaries, test outcomes, and reusable patterns",
            ),
            failure_handling=AgentFailureHandling(fallback_brain="MiniMax/Coding via Ollama"),
        ),
        "job_application_agent": SaturnixAgentBlueprint(
            agent_name="Job Application Agent",
            purpose="Tailor resumes, cover letters, outreach, and application material to a role.",
            best_brain="GPT",
            inputs=[
                AgentInputDefinition(name="job_description", description="Target job description."),
                AgentInputDefinition(name="candidate_profile", description="Resume, skills, history, or notes."),
                AgentInputDefinition(
                    name="tone",
                    description="Desired writing style and regional expectations.",
                    required=False,
                ),
            ],
            tools=["memory_search", "document_template", "ats_checker"],
            workflow_steps=[
                AgentWorkflowStepDefinition(
                    order=1,
                    name="Map Requirements",
                    description="Extract role requirements and priority keywords.",
                    expected_output="Role requirement map.",
                ),
                AgentWorkflowStepDefinition(
                    order=2,
                    name="Match Candidate Evidence",
                    description="Connect candidate experience to job requirements.",
                    expected_output="Evidence-to-requirement matrix.",
                ),
                AgentWorkflowStepDefinition(
                    order=3,
                    name="Generate Application Assets",
                    description="Draft tailored application content.",
                    expected_output="Resume bullets, cover letter, or outreach draft.",
                ),
            ],
            output_format="tailored markdown or document-ready sections",
            validation_rules=[
                AgentValidationRule(
                    name="truthfulness",
                    description="Do not invent experience, credentials, employers, or metrics.",
                    severity="critical",
                ),
                AgentValidationRule(
                    name="role_alignment",
                    description="Output should address the target job requirements directly.",
                    severity="high",
                ),
            ],
            memory_rules=AgentMemoryRules(
                namespace="agent:job_application",
                recall_policy="retrieve approved profile facts and prior application preferences",
                write_policy="store reusable approved bullets and role-specific notes only",
            ),
            failure_handling=AgentFailureHandling(fallback_brain="Claude"),
        ),
        "semiconductor_agent": SaturnixAgentBlueprint(
            agent_name="Semiconductor Agent",
            purpose="Analyze semiconductor companies, fabrication flows, chip architectures, and market context.",
            best_brain="Claude",
            inputs=[
                AgentInputDefinition(name="analysis_target", description="Company, chip, node, market, or process."),
                AgentInputDefinition(
                    name="technical_context",
                    description="Specs, datasheets, filings, notes, or benchmarks.",
                    required=False,
                ),
                AgentInputDefinition(
                    name="analysis_depth",
                    description="Requested depth: quick summary, technical deep dive, or strategic analysis.",
                    required=False,
                ),
            ],
            tools=["memory_search", "document_parser", "structured_extractor"],
            workflow_steps=[
                AgentWorkflowStepDefinition(
                    order=1,
                    name="Classify Topic",
                    description="Determine whether the task is technical, market, supply-chain, or strategic.",
                    expected_output="Topic classification and scope.",
                ),
                AgentWorkflowStepDefinition(
                    order=2,
                    name="Analyze Evidence",
                    description="Compare technical claims, constraints, and market implications.",
                    expected_output="Analysis notes.",
                ),
                AgentWorkflowStepDefinition(
                    order=3,
                    name="Produce Semiconductor Brief",
                    description="Return a precise brief with risks, assumptions, and confidence.",
                    expected_output="Semiconductor analysis brief.",
                ),
            ],
            output_format="technical brief with assumptions and confidence levels",
            validation_rules=[
                AgentValidationRule(
                    name="technical_precision",
                    description="Separate known facts from inference and avoid unsupported process-node claims.",
                    severity="high",
                ),
                AgentValidationRule(
                    name="date_sensitivity",
                    description="Flag time-sensitive market or company information for refresh.",
                    severity="high",
                ),
            ],
            memory_rules=AgentMemoryRules(
                namespace="agent:semiconductor",
                recall_policy="retrieve known company, node, architecture, and market notes",
                write_policy="store durable technical definitions and analysis summaries",
            ),
            failure_handling=AgentFailureHandling(fallback_brain="GPT"),
        ),
        "automation_agent": SaturnixAgentBlueprint(
            agent_name="Automation Agent",
            purpose="Design and execute structured automation workflows with tool/function calls.",
            best_brain="Gemini",
            inputs=[
                AgentInputDefinition(name="automation_goal", description="Workflow outcome to automate."),
                AgentInputDefinition(
                    name="available_tools",
                    description="Tool names, schemas, credentials, or external systems.",
                    required=False,
                ),
                AgentInputDefinition(
                    name="trigger",
                    description="Manual, scheduled, webhook, or event-based trigger.",
                    required=False,
                ),
            ],
            tools=["function_router", "n8n_webhook_optional", "current_time"],
            workflow_steps=[
                AgentWorkflowStepDefinition(
                    order=1,
                    name="Model Workflow",
                    description="Break automation into deterministic steps and decision points.",
                    expected_output="Workflow graph.",
                ),
                AgentWorkflowStepDefinition(
                    order=2,
                    name="Prepare Tool Calls",
                    description="Create schema-valid tool/function call payloads.",
                    expected_output="Validated tool call plan.",
                ),
                AgentWorkflowStepDefinition(
                    order=3,
                    name="Execution Readiness Check",
                    description="Confirm permissions, inputs, and rollback behavior.",
                    expected_output="Ready-to-run automation spec.",
                ),
            ],
            output_format="strict JSON workflow specification",
            validation_rules=[
                AgentValidationRule(
                    name="schema_validity",
                    description="All tool calls must match declared schemas.",
                    severity="critical",
                ),
                AgentValidationRule(
                    name="side_effect_safety",
                    description="Potentially destructive or external side effects must require confirmation.",
                    severity="critical",
                ),
            ],
            memory_rules=AgentMemoryRules(
                namespace="agent:automation",
                recall_policy="retrieve approved workflows, tool schemas, and user automation preferences",
                write_policy="store successful workflow specs, failures, and permission notes",
            ),
            failure_handling=AgentFailureHandling(fallback_brain="GPT"),
        ),
        "voice_agent": SaturnixAgentBlueprint(
            agent_name="Voice Agent",
            purpose="Handle speech-to-text, text-to-speech, and voice interaction flows.",
            best_brain="Groq",
            inputs=[
                AgentInputDefinition(name="audio_or_transcript", description="Audio bytes, audio file, or transcript."),
                AgentInputDefinition(
                    name="interaction_goal",
                    description="Desired voice workflow outcome.",
                    required=False,
                ),
            ],
            tools=["groq_transcription", "voice_prompt_adapter"],
            workflow_steps=[
                AgentWorkflowStepDefinition(
                    order=1,
                    name="Transcribe Or Normalize",
                    description="Convert speech to accurate text or normalize a transcript.",
                    expected_output="Clean transcript.",
                ),
                AgentWorkflowStepDefinition(
                    order=2,
                    name="Extract Spoken Intent",
                    description="Identify task, constraints, and response mode.",
                    expected_output="Execution-ready spoken intent.",
                ),
                AgentWorkflowStepDefinition(
                    order=3,
                    name="Prepare Voice Response",
                    description="Return concise response content suitable for speech.",
                    expected_output="Voice response payload.",
                ),
            ],
            output_format="transcript plus voice-ready response",
            validation_rules=[
                AgentValidationRule(
                    name="transcription_uncertainty",
                    description="Ambiguous transcript spans must be flagged before execution.",
                    severity="high",
                ),
                AgentValidationRule(
                    name="voice_brevity",
                    description="Voice responses should be concise and easy to speak.",
                ),
            ],
            memory_rules=AgentMemoryRules(
                namespace="agent:voice",
                recall_policy="retrieve voice preferences and recent conversational context",
                write_policy="store only user-approved voice preferences and durable instructions",
            ),
            failure_handling=AgentFailureHandling(fallback_brain="GPT"),
        ),
        "memory_agent": SaturnixAgentBlueprint(
            agent_name="Memory Agent",
            purpose="Store, retrieve, deduplicate, and govern framework memory.",
            best_brain="Gemma via Ollama",
            inputs=[
                AgentInputDefinition(name="memory_query_or_record", description="Information to store or retrieve."),
                AgentInputDefinition(
                    name="namespace",
                    description="Memory namespace to use.",
                    required=False,
                ),
                AgentInputDefinition(
                    name="memory_operation",
                    description="Operation: recall, write, update, deduplicate, or summarize.",
                    required=False,
                ),
            ],
            tools=["memory_search", "memory_write", "vector_search"],
            workflow_steps=[
                AgentWorkflowStepDefinition(
                    order=1,
                    name="Classify Memory Operation",
                    description="Determine whether to read, write, update, or ignore.",
                    expected_output="Memory operation plan.",
                ),
                AgentWorkflowStepDefinition(
                    order=2,
                    name="Apply Memory Rules",
                    description="Check privacy, durability, namespace, and duplication rules.",
                    expected_output="Approved memory action.",
                ),
                AgentWorkflowStepDefinition(
                    order=3,
                    name="Return Memory Result",
                    description="Provide retrieved memories or a write confirmation.",
                    expected_output="Memory result.",
                ),
            ],
            output_format="structured memory operation result",
            validation_rules=[
                AgentValidationRule(
                    name="privacy_filter",
                    description="Do not store sensitive or transient information unless explicitly approved.",
                    severity="critical",
                ),
                AgentValidationRule(
                    name="deduplication",
                    description="Avoid duplicate or contradictory memory records.",
                    severity="high",
                ),
            ],
            memory_rules=AgentMemoryRules(
                namespace="agent:memory",
                recall_policy="retrieve relevant memories by namespace and semantic similarity",
                write_policy="write durable, user-approved, non-sensitive memory summaries",
            ),
            failure_handling=AgentFailureHandling(fallback_brain="GPT"),
        ),
        "verification_agent": SaturnixAgentBlueprint(
            agent_name="Verification Agent",
            purpose="Validate outputs against intent, constraints, schemas, and safety requirements.",
            best_brain="GPT",
            inputs=[
                AgentInputDefinition(name="original_goal", description="The original user or system goal."),
                AgentInputDefinition(name="candidate_output", description="The output to verify."),
                AgentInputDefinition(
                    name="acceptance_criteria",
                    description="Rules, tests, or schema requirements.",
                    required=False,
                ),
            ],
            tools=["schema_validator", "test_runner", "memory_search"],
            workflow_steps=[
                AgentWorkflowStepDefinition(
                    order=1,
                    name="Map Acceptance Criteria",
                    description="Extract explicit and implied requirements.",
                    expected_output="Verification checklist.",
                ),
                AgentWorkflowStepDefinition(
                    order=2,
                    name="Evaluate Output",
                    description="Check correctness, completeness, safety, and format.",
                    expected_output="Findings with severity.",
                ),
                AgentWorkflowStepDefinition(
                    order=3,
                    name="Recommend Fixes",
                    description="Provide focused remediation steps or improved output.",
                    expected_output="Verification verdict and fixes.",
                ),
            ],
            output_format="verification report with pass/fail, score, findings, and fixes",
            validation_rules=[
                AgentValidationRule(
                    name="evidence_based_findings",
                    description="Findings must point to a concrete mismatch or risk.",
                    severity="high",
                ),
                AgentValidationRule(
                    name="no_false_confidence",
                    description="Do not pass outputs with untested high-risk assumptions.",
                    severity="high",
                ),
            ],
            memory_rules=AgentMemoryRules(
                namespace="agent:verification",
                recall_policy="retrieve prior failure patterns and acceptance preferences",
                write_policy="store recurring defects, test outcomes, and accepted verification policies",
            ),
            failure_handling=AgentFailureHandling(fallback_brain="Claude"),
        ),
    }

