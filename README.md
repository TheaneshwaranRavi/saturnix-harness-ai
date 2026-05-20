# SATURNIX-HARNESS

SATURNIX-HARNESS is a backend-first Python framework for constructing, routing,
executing, verifying, and improving agentic AI systems.

It is designed as an expandable foundation for multi-agent applications that can
use cloud brains, local Ollama models, persistent memory, voice interfaces, and
structured workflow execution through a clean FastAPI and CLI-ready architecture.

## Project Vision

SATURNIX-HARNESS exists to make agentic AI systems easier to design, compose,
run, inspect, and improve.

The long-term vision is a construction harness where a human states intent once,
and SATURNIX maps that intent into the right agent architecture, routes each task
to the right AI brain, executes the workflow, verifies results, remembers useful
state, and improves over time.

The framework is intentionally modular:

- Bring your own cloud model APIs.
- Run local/private tasks through Ollama.
- Construct specialized agents dynamically.
- Persist structured and vector memory.
- Expose workflows through FastAPI.
- Add edge nodes later, including Raspberry Pi devices.

## HARNESS Meaning

```text
H = Human Intent Mapping
A = Agent Architecture Design
R = Resource and Brain Routing
N = Navigation Workflow
E = Execution Engine
S = Self-Verification Loop
S = System Memory and Scaling
```

In practice:

1. Human Intent Mapping turns a user goal into structured intent.
2. Agent Architecture Design builds the required specialized agents.
3. Resource and Brain Routing selects the best brain for the task.
4. Navigation Workflow creates a step-by-step execution plan.
5. Execution Engine runs the workflow and captures traces.
6. Self-Verification Loop validates and can improve outputs.
7. System Memory and Scaling stores useful knowledge and prepares for larger deployments.

## Architecture Diagram

```text
                         +----------------------+
                         |      User / API      |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |      FastAPI App     |
                         |  saturnix_harness    |
                         +----------+-----------+
                                    |
                                    v
          +-------------------------+-------------------------+
          |                 Core Orchestrator                 |
          +-------------------------+-------------------------+
                                    |
       +----------------------------+-----------------------------+
       |                            |                             |
       v                            v                             v
+--------------+           +----------------+            +----------------+
| Intent Mapper|           | Agent          |            | Brain Router   |
|              |           | Constructor    |            |                |
+------+-------+           +-------+--------+            +-------+--------+
       |                           |                             |
       v                           v                             v
+--------------+           +----------------+       +--------------------------+
| Workflow     |           | Agent Runtime  |       | Cloud and Local Brains  |
| Builder      |           | + Tools        |       | GPT, Claude, Gemini,   |
+------+-------+           +-------+--------+       | Ollama, Groq           |
       |                           |                +-------------+------------+
       v                           v                              |
+--------------+           +----------------+                     |
| Execution    +---------->| Verification   |<--------------------+
| Engine       |           | Engine         |
+------+-------+           +-------+--------+
       |                           |
       v                           v
+--------------+           +----------------+
| SQLite       |           | ChromaDB       |
| Memory       |           | Vector Memory  |
+--------------+           +----------------+
```

## Supported AI Brains

| Brain | Best for | Provider |
| --- | --- | --- |
| GPT / ChatGPT API | Reasoning, coding, planning, orchestration, architecture | OpenAI |
| Claude API | Long documents, deep analysis, large context, document understanding | Anthropic |
| Gemini | Structured JSON, schema-based output, function calling | Google DeepMind |
| Gemma via Ollama | Local/private lightweight execution | Ollama |
| MiniMax / Qwen Coder / DeepSeek Coder via Ollama | Fast local coding and code generation | Ollama |
| Groq | Speech-to-text, text-to-speech, voice interaction | Groq |
| Mock Brain | Offline tests, local smoke tests, first-run development | SATURNIX |

## Repository Structure

```text
SATURNIX-HARNESS/
  saturnix_harness/
    api/                 FastAPI routes and dependency wiring
    agents/              Agent runtime, blueprints, default agent catalog
    brains/              Brain providers and routing logic
    core/                Intent, workflow, execution, verification, orchestration
    dashboard/           Infrastructure dashboard services, security, data guardian
    memory/              SQLite structured memory and ChromaDB vector memory
    monitoring/          Logging and runtime event capture
    prompts/             Packaged prompt templates
    tools/               Tool contracts and built-in tools
    voice/               Groq STT, TTS, command extraction, voice workflows
    cli.py               Command-line interface
    config.py            Environment-driven settings
    main.py              FastAPI app factory
    schemas.py           Pydantic contracts
  examples/              Example agents and workflows
  frontend/              Next.js infrastructure dashboard
  tests/                 Unit and integration tests
  data/                  Local runtime data mount
  Dockerfile
  docker-compose.yml
  pyproject.toml
  requirements.txt
  .env.example
  README.md
```

## Installation

Requirements:

- Python 3.11 or newer
- pip
- Optional: Docker and Docker Compose
- Optional: Ollama for local models

Install locally:

```bash
cd SATURNIX-HARNESS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m pytest
```

Install as an editable package:

```bash
pip install -e .
```

## .env Setup

SATURNIX reads configuration from `.env`. Start from the template:

```bash
cp .env.example .env
```

Core values:

```env
SATURNIX_ENV=development
SATURNIX_LOG_LEVEL=INFO
SATURNIX_API_HOST=0.0.0.0
SATURNIX_API_PORT=8088

SATURNIX_ENABLE_MOCK_BRAINS=true
SATURNIX_ENABLE_OLLAMA=false
SATURNIX_DEFAULT_BRAIN=openai
SATURNIX_LOCAL_ONLY=false
```

Cloud brain keys:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1

ANTHROPIC_API_KEY=
CLAUDE_MODEL=claude-3-7-sonnet-latest

GOOGLE_API_KEY=
GEMINI_MODEL=gemini-2.0-flash

GROQ_API_KEY=
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3-turbo
GROQ_TTS_MODEL=canopylabs/orpheus-v1-english
GROQ_TTS_VOICE=troy
GROQ_TTS_RESPONSE_FORMAT=wav
```

Memory:

```env
SATURNIX_SQLITE_PATH=./data/saturnix.sqlite3
SATURNIX_CHROMA_PATH=./data/chroma
SATURNIX_ENABLE_CHROMA=true
```

Dashboard security:

```env
SATURNIX_DASHBOARD_AUTH_REQUIRED=false
SATURNIX_JWT_SECRET=
SATURNIX_DASHBOARD_ENCRYPTION_KEY=
SATURNIX_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
SATURNIX_RATE_LIMIT_PER_MINUTE=120
SATURNIX_LOCKDOWN_MODE=false
SATURNIX_ALLOWED_STORAGE_ROOTS=./data,./backups
NEXT_PUBLIC_SATURNIX_API_BASE=http://localhost:8088
```

Never hardcode API keys in source files. Keep secrets in `.env` or your
deployment secret manager.

## Ollama Setup

Install Ollama from:

```text
https://ollama.com
```

Start Ollama locally:

```bash
ollama serve
```

SATURNIX expects Ollama at:

```text
http://localhost:11434
```

Pull supported models:

```bash
ollama pull gemma3
ollama pull deepseek-coder-v2
ollama pull qwen2.5-coder
ollama pull minimax
```

Enable Ollama in `.env`:

```env
SATURNIX_ENABLE_OLLAMA=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_GEMMA_MODEL=gemma3
OLLAMA_CODING_MODEL=deepseek-coder-v2
OLLAMA_MINIMAX_MODEL=minimax
OLLAMA_QWEN_CODER_MODEL=qwen2.5-coder
OLLAMA_DEEPSEEK_CODER_MODEL=deepseek-coder-v2
OLLAMA_REQUEST_TIMEOUT=120
```

Check Ollama through SATURNIX:

```bash
curl http://localhost:8088/v1/ollama/health
```

If Ollama is not running, direct Ollama generation helpers return structured
fallback results. Brain-router execution can continue through configured
fallback brains.

## Run FastAPI

Development server:

```bash
uvicorn saturnix_harness.main:app --reload --host 0.0.0.0 --port 8088
```

Open API docs:

```text
http://localhost:8088/docs
```

Health check:

```bash
curl http://localhost:8088/v1/health
```

## Phase 1 MVP Endpoints

The Phase 1 backend exposes four root endpoints:

- `GET /health`: service health, tools, and brain status
- `POST /execute`: run the SATURNIX orchestrator for a user goal
- `GET /agents`: list Phase 1 default agents
- `GET /brains`: list configured brain providers

Run an execution:

```bash
curl -X POST http://localhost:8088/execute \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Design a Phase 1 SATURNIX research workflow with verification",
    "task_type": "architecture",
    "privacy_level": "standard",
    "speed_priority": "normal",
    "context_size": "medium",
    "output_format": "markdown"
  }'
```

Example response:

```json
{
  "goal": "Design a Phase 1 SATURNIX research workflow with verification",
  "detected_intent": "Design a Phase 1 SATURNIX research workflow with verification",
  "agents_used": ["saturnix_architect", "saturnix_verifier"],
  "brain_routing": {
    "selected_brain": "GPT",
    "fallback_brain": "Claude"
  },
  "workflow": [],
  "execution_result": {
    "ok": true,
    "output": "..."
  },
  "validation_result": {
    "ok": true,
    "score": 1.0,
    "findings": []
  },
  "memory_saved": {
    "namespace": "saturnix:execution",
    "phase1_tables": {
      "user_goal_id": "...",
      "agent_run_ids": ["..."],
      "brain_route_id": "...",
      "verification_result_id": "..."
    }
  },
  "next_actions": []
}
```

## Docker

Run the API and Ollama service with Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

Services:

- `saturnix-api`: FastAPI on port `8088`
- `saturnix-dashboard`: Next.js dashboard on port `3000`
- `ollama`: Ollama daemon on port `11434`
- `data`: local SQLite and Chroma storage mount

Pull Ollama models inside Docker:

```bash
docker compose exec ollama ollama pull gemma3
docker compose exec ollama ollama pull deepseek-coder-v2
docker compose exec ollama ollama pull qwen2.5-coder
docker compose exec ollama ollama pull minimax
```

## Infrastructure Dashboard

SATURNIX-HARNESS includes a dark, cybersecurity-focused infrastructure
dashboard for controlling and monitoring the personal AI operating model.

```text
Browser Dashboard
  |
  v
Next.js + TypeScript + Tailwind + shadcn-style components
  |
  v
FastAPI Dashboard API
  |
  +-- Agent Control Center
  +-- Brain Router Monitor
  +-- Memory Vault Dashboard
  +-- Security Command Center
  +-- Data Protection Center
  +-- Workflow Automation Panel
  +-- Raspberry Pi Edge Node Monitor
  +-- Voice Agent Console
  +-- API Key Management Panel
  +-- Logs and Audit Trail
  +-- Backup and Recovery Panel
  +-- System Health and Analytics
```

Run the backend:

```bash
uvicorn saturnix_harness.main:app --reload --host 0.0.0.0 --port 8088
```

Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

Dashboard API endpoints:

- `GET /health`
- `GET /dashboard/overview`
- `GET /dashboard/doctrine`
- `GET /agents`
- `POST /agents/create`
- `POST /agents/execute`
- `GET /brains`
- `POST /brains/route`
- `GET /memory`
- `POST /memory/save`
- `POST /memory/search`
- `GET /security/status`
- `GET /security/audit-logs`
- `POST /security/scan-input`
- `POST /security/lockdown`
- `GET /edge/pi/status`
- `GET /storage/status`
- `GET /workflows`
- `POST /workflows/run`
- `GET /voice/status`
- `POST /voice/transcribe`
- `GET /logs`
- `GET /api-keys`
- `POST /api-keys/store`
- `GET /profile`
- `POST /data/classify`

Example dashboard security scan:

```bash
curl -X POST http://localhost:8088/security/scan-input \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "Summarize this workflow and protect API keys.",
    "source": "dashboard"
  }'
```

Example response:

```json
{
  "security_score": 100,
  "threat_level": "LOW",
  "detected_risks": [],
  "blocked_actions": [],
  "recommended_fixes": ["No immediate security issues detected."],
  "lockdown_required": false
}
```

## SATURNIX Operating Doctrine

SATURNIX-HARNESS is not a chatbot. It is a personalized AI infrastructure
system that must behave as:

- AI operating dashboard
- Secure agent manager
- Personal memory vault
- Cyber-defense layer
- Workflow automation engine
- Local/cloud brain router
- Self-improving engineering harness

The operating doctrine is exposed at:

```bash
curl http://localhost:8088/dashboard/doctrine
```

Core principles:

- Security first
- Privacy first
- Personalization first
- Verification before execution
- Minimum required permissions
- Local-first memory
- Multi-brain intelligence
- Human approval for risky actions
- Full audit trail
- Continuous improvement

The dashboard execution path enforces this doctrine before agent execution. A
high-risk non-dry-run request without approval returns a blocked response with
`confirmation_required: true`, the security scan, data classification, and the
principles enforced.

## Dashboard Security Architecture

SATURNIX Security Sentinel protects the dashboard with:

- JWT authentication support for protected deployments
- Role checks for admin-only actions such as lockdown and API key writes
- Rate limiting middleware for API endpoints
- Secure response headers
- CORS allowlisting
- Prompt injection detection
- Secret exposure detection and redaction
- Suspicious path and path traversal detection
- Unsafe command and dangerous workflow blocking
- Audit logging for sensitive actions
- Emergency lockdown mode

Security output schema:

```json
{
  "security_score": 0,
  "threat_level": "LOW | MEDIUM | HIGH | CRITICAL",
  "detected_risks": [],
  "blocked_actions": [],
  "recommended_fixes": [],
  "lockdown_required": false
}
```

## Data Guardian

SATURNIX Data Guardian classifies data before memory or storage actions.

Supported data classes:

- `public_data`
- `project_data`
- `personal_memory`
- `api_secrets`
- `agent_logs`
- `voice_records`
- `critical_backups`

Sensitive classes are encrypted before storage. Memory rules block raw
passwords, unencrypted API keys, unnecessary sensitive personal data, and
private documents unless the user grants permission.

## Dashboard Agents

The dashboard ships with least-privilege defaults:

- Personal Assistant Agent
- Coding Agent
- Research Agent
- Security Agent
- Memory Agent
- Workflow Agent
- Voice Agent
- Raspberry Pi Edge Agent
- Job Application Agent
- Semiconductor Design Agent

Permissions are explicit and minimal:

- `READ_ONLY`
- `MEMORY_WRITE`
- `TOOL_EXECUTION`
- `FILE_ACCESS`
- `NETWORK_ACCESS`
- `ADMIN_SECURITY`

Zero-trust rule: no agent is trusted by default. Every sensitive action is
validated before execution, and high-risk actions require confirmation.

## Example API Request

Run the full SATURNIX execution engine:

```bash
curl -X POST http://localhost:8088/v1/execution/run \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Design a three-agent research workflow that analyzes a document, returns JSON, and verifies the final answer.",
    "input": "Prefer Claude for long context and Gemini for schema-valid JSON.",
    "task_type": "architecture",
    "privacy_level": "standard",
    "speed_priority": "normal",
    "context_size": "large",
    "output_format": "markdown",
    "auto_improve": true
  }'
```

Response shape:

```json
{
  "goal": "",
  "detected_intent": "",
  "agents_used": [],
  "brain_routing": {},
  "workflow": [],
  "execution_result": {},
  "validation_result": {},
  "memory_saved": {},
  "next_actions": []
}
```

Every SATURNIX execution also runs the Recursive Improvement Engine. The
optimization report is returned under:

```text
execution_result.recursive_improvement
```

That report includes failure analysis, bottlenecks, hallucination risk, wasted
tokens, weak workflows, repeated mistakes, architecture improvements, prompt
upgrades, routing improvements, execution improvements, memory improvements,
and stored optimization strategy IDs.

Analyze a previous execution result directly:

```bash
curl -X POST http://localhost:8088/v1/improvement/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Build a private coding workflow with verification",
    "detected_intent": "private coding workflow",
    "agents_used": ["coding_agent"],
    "brain_routing": {"selected_brain": "GPT", "fallback_brain": "Claude"},
    "workflow": [{"name": "Execute", "prompt": "Build workflow"}],
    "execution_result": {"ok": false, "output": "This is guaranteed to always work."},
    "validation_result": {"ok": false, "score": 0.4, "findings": ["Hallucination risk"]},
    "memory_saved": {},
    "next_actions": []
  }'
```

Construct or reuse specialized agents automatically:

```bash
curl -X POST http://localhost:8088/v1/agents/autonomous-construct \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Threat model a private automation workflow with permissions and secrets",
    "task_type": "security",
    "privacy_level": "private",
    "required_tools": ["permission_checker"],
    "security_requirements": ["no external secrets"],
    "memory_needs": ["failed workflows"]
  }'
```

The autonomous constructor analyzes task complexity, expertise, tools, security,
cost, and memory needs. It reuses default agents first, creates missing
specialists only when needed, stores new dynamic blueprints in
`saturnix:agents`, and returns `created_agents`, `reused_agents`, and
`duplicate_agents_avoided`.

Plan a dependency-aware workflow graph:

```bash
curl -X POST http://localhost:8088/v1/workflows/plan \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Build a private FastAPI automation workflow with JSON schema, memory, security review, and verification",
    "task_type": "architecture",
    "privacy_level": "private",
    "speed_priority": "normal",
    "output_format": "json schema",
    "max_parallelism": 3
  }'
```

The Cognitive Workflow Planner breaks complex goals into subtasks, detects
dependencies, prioritizes critical tasks, assigns agents and brains, identifies
parallel execution opportunities, estimates runtime and cost, and stores plans
under `saturnix:workflow_plans` when `persist_plan` is enabled.

Scan prompts, workflows, code, dependencies, and containers for security risk:

```bash
curl -X POST http://localhost:8088/v1/security/scan \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Summarize the approved workflow requirements.",
    "workflow": [{"action": "tool_call", "tool": "schema_validator"}],
    "code": "def add(a, b): return a + b",
    "dependencies": ["fastapi==0.115.0", "pydantic==2.7.0"],
    "container_config": "image: saturnix-api:0.1.0\nuser: app",
    "file_paths": ["/workspace/project/README.md"],
    "sensitivity_level": "standard"
  }'
```

The Security Sentinel returns `security_score`, `risks_detected`,
`recommended_fixes`, and `blocked_actions`. It redacts suspected secrets and
blocks prompt injection, unsafe execution, malicious workflows, unauthorized
file access, weak dependency sources, risky container settings, and sensitive
data exposure.

Store and recall long-term evolving intelligence:

```bash
curl -X POST http://localhost:8088/v1/neural-memory/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Successful FastAPI workflow used security checks, consensus review, and verification before execution.",
    "category": "successful_workflow",
    "title": "Secure FastAPI workflow",
    "importance_score": 0.9,
    "tags": ["fastapi", "security", "workflow"]
  }'
```

```bash
curl -X POST http://localhost:8088/v1/neural-memory/recall \
  -H "Content-Type: application/json" \
  -d '{
    "query": "FastAPI security consensus workflow",
    "limit": 5,
    "include_links": true,
    "include_summary": true
  }'
```

The Neural Memory Engine stores successful workflows, failed workflows, user
preferences, project architectures, reasoning patterns, optimization
strategies, code snippets, and reusable agent structures. It adds semantic
retrieval, ranking, aging, linking, context summaries, and compression on top of
SQLite and ChromaDB.

Select the best tools automatically:

```bash
curl -X POST http://localhost:8088/v1/tools/route \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Analyze private code snippets and recall previous security patterns",
    "task_type": "coding memory",
    "speed_requirement": "high",
    "privacy_level": "private",
    "execution_cost": "low",
    "reliability_requirement": "high",
    "scalability_requirement": "medium",
    "constraints": ["offline", "semantic retrieval"]
  }'
```

The Tool Intelligence Router scores web search, APIs, local Python, Docker,
GitHub, databases, file systems, vector memory, voice systems, and Raspberry Pi
edge nodes against speed, privacy, cost, reliability, and scalability. It
returns `selected_tools`, `tool_reasoning`, and `fallback_tools`.

Generate a production software foundation with Forge:

```bash
curl -X POST http://localhost:8088/v1/forge/build \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Build a FastAPI backend with database persistence and monitoring",
    "project_name": "Forge CRM",
    "application_type": "backend_api",
    "stack": ["Python", "FastAPI", "SQLite"],
    "features": ["contacts", "audit logs"],
    "scalability_target": "high",
    "include_docker": true,
    "include_ci": true,
    "include_monitoring": true
  }'
```

The SATURNIX Forge Coding Engine generates a typed architecture plan, folder
structure, starter source artifacts, test artifacts, Docker and CI deployment
setup, monitoring plan, and optimization report. It routes the build through
the Brain Router, selects implementation tools through the Tool Intelligence
Router, scans the construction brief with Security Sentinel, and stores the
plan in `saturnix:forge` memory when `persist_plan` is enabled.

Coordinate distributed SATURNIX hardware nodes:

```bash
curl -X POST http://localhost:8088/v1/distributed/plan \
  -H "Content-Type: application/json" \
  -d '{
    "mission": "Coordinate SATURNIX distributed intelligence nodes",
    "workloads": [
      "centralized orchestration and brain routing",
      "edge automation for Raspberry Pi sensors",
      "memory vault synchronization",
      "cloud large context analysis"
    ],
    "privacy_level": "private",
    "latency_priority": "low_latency",
    "node_health": {
      "Raspberry Pi": "healthy",
      "External Storage": "healthy"
    }
  }'
```

The Distributed Intelligence Engine coordinates:

- `MacBook M1` as the Cognitive Core for orchestration, routing, verification,
  and secret-sensitive work
- `Raspberry Pi` as the Edge Automation Node for sensors, safe local actions,
  offline queues, and signed command receipts
- `External Storage` as the Memory Vault for encrypted snapshots, backups,
  Chroma/SQLite artifacts, and recovery checkpoints
- `Cloud APIs` as Intelligence Expansion for large-context and specialized
  provider calls after privacy checks

It returns `node_assignments`, `resource_usage`, `optimization_plan`, and
`failover_strategy`.

Diagnose and recover infrastructure failures:

```bash
curl -X POST http://localhost:8088/v1/self-healing/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "containers": {
      "saturnix-api": "crashed",
      "ollama": "oom killed"
    },
    "apis": {
      "openai": "timeout",
      "gemini": "503"
    },
    "memory_usage_percent": 94,
    "disk_usage_percent": 91,
    "network_status": "degraded",
    "workflows": {
      "agent-build": "corrupted"
    },
    "processes": {
      "worker-7": "hanging for 300s"
    },
    "active_brain": "GPT",
    "fallback_brains": ["Claude", "Gemini", "Gemma via Ollama"],
    "auto_recover": true
  }'
```

The Self-Healing Infrastructure Engine monitors crashed containers, failed
APIs, memory overload, disk pressure, network failures, corrupted workflows,
and hanging processes. It returns incidents, recovery actions, fallback brain
selection, module isolation guidance, workflow rebuild steps, operator
notifications, and a resilience plan. Recovery actions are marked with
`safe_to_auto_execute` and `confirmation_required` so SATURNIX can automate
bounded repairs while protecting destructive cleanup or state changes.

Run SATURNIX-HARNESS OMEGA as the cognitive operating layer:

```bash
curl -X POST http://localhost:8088/v1/omega/run \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Build a secure multi-agent coding workflow with verification",
    "input": "Use memory, brain routing, recursive improvement, and infrastructure checks.",
    "task_type": "coding architecture",
    "privacy_level": "standard",
    "execute": true,
    "use_consensus": true,
    "persist_memory": true,
    "optimize_infrastructure": true
  }'
```

OMEGA is the top-level cognitive operating mode. It understands human intent,
creates or reuses specialized agents, routes brains and tools, constructs a
dependency-aware workflow, optionally runs multi-brain consensus, executes the
workflow, verifies results, performs recursive improvement analysis, stores
long-term neural memory, checks distributed infrastructure, and returns an
evolution plan for the next autonomous loop.

Set `"execute": false` to generate an autonomous system plan without live
execution.

Run multi-brain consensus:

```bash
curl -X POST http://localhost:8088/v1/consensus/run \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Design a hallucination-resistant routing workflow",
    "task_type": "architecture",
    "privacy_level": "standard",
    "output_format": "markdown",
    "min_brains": 2,
    "max_brains": 4,
    "include_local": true
  }'
```

The Consensus Engine queries available GPT, Claude, Gemini, and local Ollama
brains independently, compares claims, detects contradictions, estimates
confidence, and returns `consensus_result`, `brain_comparisons`,
`confidence_score`, `detected_conflicts`, and `final_reasoning`.

Route a task to the best brain:

```bash
curl -X POST http://localhost:8088/v1/brains/route \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Analyze a long contract and return key risks",
    "task_type": "deep analysis",
    "privacy_level": "standard",
    "speed_priority": "normal",
    "context_size": "large",
    "output_format": "summary"
  }'
```

Example routing response:

```json
{
  "selected_brain": "Claude",
  "reason": "Task requires long document handling, deep analysis, or a large context window.",
  "fallback_brain": "GPT",
  "execution_strategy": "Use Claude for document/context analysis. Summarize findings into compact handoff notes for downstream planning or execution."
}
```

## Example Agent Workflow

Example goal:

```text
Create a job-application workflow that analyzes a job description, rewrites
candidate bullets, checks ATS alignment, and verifies truthfulness.
```

SATURNIX flow:

```text
1. Human Intent Mapper
   Detects domain: job application
   Detects needs: writing, analysis, verification, memory

2. Brain Router
   Selects GPT for planning and writing
   Uses Claude fallback for long job descriptions or candidate documents

3. Agent Constructor
   Creates or selects:
   - Job Application Agent
   - Research Agent
   - Verification Agent

4. Workflow Builder
   Creates ordered steps:
   - Extract role requirements
   - Match candidate evidence
   - Draft tailored content
   - Verify truthfulness and alignment

5. Execution Engine
   Runs agent steps and captures traces

6. Verification Engine
   Checks output against constraints

7. Memory Manager
   Saves approved reusable profile facts and workflow summary
```

Run the bundled example:

```bash
python examples/example_workflow.py
```

## Voice Workflow

SATURNIX includes a Groq-backed voice layer:

```text
Voice input -> Groq STT -> command extraction -> SATURNIX Core -> response -> Groq TTS
```

The Voice Cognitive Agent adds session-aware conversational control:

```text
Voice Input
  -> Speech-to-Text
  -> Intent Analysis
  -> Brain Routing
  -> Memory Recall
  -> Risk Confirmation
  -> Workflow Execution
  -> Response Generation
  -> Optional Text-to-Speech
  -> Context Persistence
```

Endpoints:

- `POST /v1/voice/transcribe`
- `POST /v1/voice/tts`
- `POST /v1/voice/command`
- `POST /v1/voice/run`
- `POST /v1/voice/cognitive/turn`
- `POST /v1/voice/cognitive/run`

Low-latency transcript turn:

```bash
curl -X POST http://localhost:8088/v1/voice/cognitive/turn \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "Hey Saturnix continue the private workflow plan",
    "session_id": "demo-session",
    "low_latency_mode": true,
    "memory_limit": 5,
    "synthesize_response": false
  }'
```

Risky voice commands require confirmation before execution:

```bash
curl -X POST http://localhost:8088/v1/voice/cognitive/turn \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "Saturnix delete the production database",
    "session_id": "demo-session"
  }'
```

The response includes `confirmation_required`, `confirmation_token`,
`risk_assessment`, `stage_timings_ms`, and no `execution_result` until the user
confirms. To proceed, send a follow-up turn with the token:

```bash
curl -X POST http://localhost:8088/v1/voice/cognitive/turn \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "yes proceed",
    "session_id": "demo-session",
    "confirmation_token": "TOKEN_FROM_PREVIOUS_RESPONSE",
    "confirmed": true
  }'
```

Say `stop`, `cancel`, `interrupt`, or pass `"interrupt": true` to interrupt a
pending command before execution. Session context is persisted under
`saturnix:voice:{session_id}` memory so future turns can recall useful prior
conversation state.

Voice command extraction returns:

```json
{
  "transcript": "Hey Saturnix write private Python code quickly",
  "command_text": "write private Python code quickly",
  "task_type": "coding",
  "privacy_level": "local",
  "speed_priority": "high",
  "context_size": "small",
  "output_format": "code",
  "brain_routing": {}
}
```

## Memory System

SATURNIX memory uses SQLite for structured local memory and ChromaDB for vector
memory.

Memory types:

- `user_preferences`
- `project_history`
- `agent_execution_logs`
- `successful_workflows`
- `failed_workflows`
- `reusable_prompts`
- `code_snippets`
- `vector_memory`

Memory endpoints:

- `POST /v1/memory/save`
- `GET /v1/memory/search`
- `POST /v1/memory/search`
- `PATCH /v1/memory/{record_id}`
- `DELETE /v1/memory/{record_id}`
- `GET /v1/memory/summary`
- `POST /v1/neural-memory/store`
- `POST /v1/neural-memory/recall`
- `POST /v1/neural-memory/compress`

Example memory save:

```bash
curl -X POST http://localhost:8088/v1/memory/save \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User prefers concise technical architecture summaries.",
    "memory_type": "user_preferences",
    "namespace": "saturnix",
    "kind": "preference",
    "title": "Concise architecture summaries",
    "tags": ["style", "architecture"],
    "source": "user"
  }'
```

## MacBook M1 Local Setup Notes

SATURNIX is well-suited for Apple Silicon development.

Recommended local setup:

```bash
brew install python@3.11
brew install node
brew install ollama
ollama serve
```

Create the Python environment:

```bash
cd SATURNIX-HARNESS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start the dashboard on Apple Silicon:

```bash
uvicorn saturnix_harness.main:app --reload --port 8088
cd frontend
npm install
npm run dev
```

Useful Apple Silicon notes:

- Prefer smaller local models first, such as `gemma3`, before pulling larger coding models.
- Keep `SATURNIX_ENABLE_MOCK_BRAINS=true` during first setup so the framework runs without paid API keys.
- Enable Ollama only after `ollama serve` is running and models are pulled.
- ChromaDB can run locally, but if dependency startup is slow during early development, set `SATURNIX_ENABLE_CHROMA=false`.
- If a package has wheel issues on a newer Python version, use Python 3.11 for the smoothest dependency path.
- Keep the FastAPI backend on `localhost:8088` and the Next.js dashboard on
  `localhost:3000` unless you also update `SATURNIX_CORS_ORIGINS` and
  `NEXT_PUBLIC_SATURNIX_API_BASE`.

## Raspberry Pi Edge-Node Future Plan

SATURNIX is designed to support future edge-node deployments where Raspberry Pi
devices can act as lightweight local workers.

Planned edge-node responsibilities:

- Local command intake from microphone, sensors, or device APIs
- Lightweight task classification
- Local memory cache and sync
- Secure relay to a central SATURNIX Core server
- Offline-first workflows for simple local tasks
- Health reporting from field devices

Potential architecture:

```text
Raspberry Pi Edge Node
  |
  +-- Local microphone / sensors / scripts
  +-- Lightweight command parser
  +-- Local SQLite cache
  +-- Optional tiny local model
  |
  v
SATURNIX Core Server
  |
  +-- Full brain routing
  +-- Agent construction
  +-- Chroma vector memory
  +-- Verification and workflow execution
```

Future edge transport options:

- MQTT for low-bandwidth device messaging
- HTTPS callbacks for command dispatch
- WebSockets for live voice sessions
- Signed payloads for trusted edge-node identity

## Cybersecurity Checklist

Before using SATURNIX-HARNESS with real credentials or private data:

- Keep API keys in `.env` or a secret manager only.
- Set `SATURNIX_DASHBOARD_AUTH_REQUIRED=true` outside local development.
- Set a strong `SATURNIX_JWT_SECRET`.
- Set a unique `SATURNIX_DASHBOARD_ENCRYPTION_KEY`.
- Restrict `SATURNIX_CORS_ORIGINS` to trusted dashboard origins.
- Keep `SATURNIX_ALLOWED_STORAGE_ROOTS` narrow.
- Run security scans before executing generated workflows.
- Confirm high-risk file, network, tool, and admin actions manually.
- Do not store raw passwords or unencrypted API keys in memory.
- Review `/security/audit-logs` and `/logs` after sensitive actions.
- Test lockdown mode before relying on it operationally.
- Run containers as non-root users.
- Back up SQLite, Chroma, and dashboard configuration regularly.

## Roadmap

Near term:

- Add browser push updates for live dashboard metrics
- Add dashboard login and token issuance UI
- Add richer tool schemas and tool execution permissions
- Add request/response tracing for every brain call
- Add n8n webhook tool integration
- Add API auth and per-user namespaces
- Add workflow persistence and replay

Medium term:

- Add streaming execution events
- Add persistent dashboard widgets for runs, agents, memory, and brain health
- Add evaluation harness for comparing brain outputs
- Add local embedding model support for Chroma
- Add agent marketplace-style blueprint registry
- Add Raspberry Pi signed command agent

Long term:

- Raspberry Pi edge-node mode
- Distributed worker execution
- Voice-first SATURNIX command center
- Multi-project memory isolation
- Human approval gates for high-risk tool actions
- Production deployment templates for cloud and homelab environments
- External storage vault synchronization and encrypted recovery snapshots

## Testing

The test suite runs without live API keys by using mock providers and local
SQLite memory:

```bash
python3 -m pytest
```

Current implemented areas include:

- SATURNIX-HARNESS OMEGA
- Brain Router
- Agent Constructor
- Autonomous Agent Constructor
- Cognitive Workflow Planner
- Consensus Engine
- Security Sentinel
- Execution Engine
- Tool Intelligence Router
- Forge Coding Engine
- Distributed Intelligence Engine
- Self-Healing Infrastructure Engine
- Memory Manager
- Neural Memory Engine
- Ollama Provider
- Voice Engine
- Voice Cognitive Agent
- Recursive Improvement Engine
- Prompt loading
- Configuration

## License

No license has been selected yet. Add one before public distribution.
