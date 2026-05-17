from __future__ import annotations

import json
import re

from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.core.security_sentinel import SecuritySentinel
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.schemas import (
    BrainRouteRequest,
    ForgeArchitectureComponent,
    ForgeArchitecturePlan,
    ForgeArtifact,
    ForgeBuildRequest,
    ForgeBuildResult,
    ForgeDeploymentSetup,
    ForgeFolderItem,
    ForgeMonitoringSetup,
    MemoryType,
    SaveMemoryRequest,
    SecurityScanRequest,
    ToolRoutingRequest,
)
from saturnix_harness.tools.intelligence_router import ToolIntelligenceRouter


class ForgeCodingEngine:
    """SATURNIX Forge Coding Engine.

    Forge converts a software goal into production-oriented construction
    artifacts. It is deterministic in the MVP, but it routes brains and tools so
    the generated plan can later be handed to live model-backed builders.
    """

    def __init__(
        self,
        brain_router: BrainRouter,
        tool_router: ToolIntelligenceRouter,
        memory: MemoryManager,
        security_sentinel: SecuritySentinel,
    ) -> None:
        self.brain_router = brain_router
        self.tool_router = tool_router
        self.memory = memory
        self.security_sentinel = security_sentinel

    def build(self, request: ForgeBuildRequest) -> ForgeBuildResult:
        project_slug = _slugify(request.project_name)
        route = self.brain_router.route_task(
            BrainRouteRequest(
                task=request.goal,
                task_type=_task_type(request),
                privacy_level=request.privacy_level,
                speed_priority=request.speed_requirement,
                context_size="large",
                output_format="code and deployment artifacts",
            )
        )
        tool_route = self.tool_router.route(
            ToolRoutingRequest(
                task=_tool_routing_task(request),
                task_type=_task_type(request),
                speed_requirement=request.speed_requirement,
                privacy_level=request.privacy_level,
                execution_cost="balanced",
                reliability_requirement="high",
                scalability_requirement=request.scalability_target,
                constraints=request.constraints,
            )
        )
        selected_tools = _forge_selected_tools(request, tool_route.selected_tools)
        security = self.security_sentinel.scan(
            SecurityScanRequest(
                task=request.goal,
                dependencies=request.stack,
                actions=request.features,
                sensitivity_level=request.privacy_level,
            )
        )

        architecture = _architecture_plan(request, route.selected_brain, selected_tools)
        folder_structure = _folder_structure(request, project_slug)
        implementation = _implementation_artifacts(request, project_slug)
        tests = _test_artifacts(request, project_slug)
        deployment = _deployment_setup(request, project_slug)
        monitoring = _monitoring_setup(request)
        optimization = _optimization_report(
            request=request,
            selected_brain=route.selected_brain,
            selected_tools=selected_tools,
            tool_reasoning=tool_route.tool_reasoning,
            security_score=security.security_score,
            security_risks=security.risks_detected,
        )
        result = ForgeBuildResult(
            architecture_plan=architecture,
            folder_structure=folder_structure,
            implementation=implementation,
            tests=tests,
            deployment_setup=deployment,
            monitoring_setup=monitoring,
            optimization_report=optimization,
        )
        if request.persist_plan:
            record = self.memory.save_memory(
                SaveMemoryRequest(
                    content=json.dumps(result.model_dump(mode="json"), indent=2),
                    memory_type=MemoryType.project_history,
                    namespace="saturnix:forge",
                    kind="forge_build_plan",
                    title=request.project_name[:120],
                    tags=["forge", "coding_engine", _task_type(request)],
                    metadata={
                        "goal": request.goal,
                        "project_name": request.project_name,
                        "selected_brain": route.selected_brain,
                        "selected_tools": selected_tools,
                    },
                    source="forge_coding_engine",
                )
            )
            result.memory_saved = {
                "namespace": record.namespace,
                "record_id": record.id,
                "kind": record.kind,
            }
        return result


def _architecture_plan(
    request: ForgeBuildRequest,
    selected_brain: str,
    selected_tools: list[str],
) -> ForgeArchitecturePlan:
    components = [
        ForgeArchitectureComponent(
            name="API Boundary",
            purpose="Expose stable HTTP contracts for the product surface.",
            responsibilities=[
                "Validate request payloads with Pydantic models.",
                "Return typed responses with consistent error envelopes.",
                "Keep route handlers thin and delegate business logic to services.",
            ],
            interfaces=["FastAPI router", "OpenAPI schema", "health endpoint"],
            scaling_notes=[
                "Keep route modules versioned under /api/v1.",
                "Use stateless request handling so replicas can scale horizontally.",
            ],
        ),
        ForgeArchitectureComponent(
            name="Domain Service Layer",
            purpose="Hold business rules and orchestration away from framework code.",
            responsibilities=[
                "Implement feature workflows as reusable service classes.",
                "Coordinate persistence, external APIs, and validation.",
                "Raise domain-specific errors for predictable API behavior.",
            ],
            interfaces=["service classes", "repository ports", "typed DTOs"],
            scaling_notes=[
                "Split high-traffic workflows into workers when queue pressure grows.",
                "Keep side effects behind interfaces for testability.",
            ],
        ),
    ]
    if request.include_database:
        components.append(
            ForgeArchitectureComponent(
                name="Persistence Layer",
                purpose="Store durable application state with migration-friendly schemas.",
                responsibilities=[
                    "Define repository interfaces around database operations.",
                    "Separate database models from API request models.",
                    "Protect writes with transactions and idempotency keys.",
                ],
                interfaces=["SQL repository", "migration scripts", "connection settings"],
                scaling_notes=[
                    "Add read replicas for query-heavy workloads.",
                    "Use indexes for user-facing lookup and filtering paths.",
                ],
            )
        )
    if request.include_frontend:
        components.append(
            ForgeArchitectureComponent(
                name="Frontend Application",
                purpose="Provide a focused user interface over the backend API.",
                responsibilities=[
                    "Render core workflows with accessible components.",
                    "Call typed API clients generated from OpenAPI contracts.",
                    "Surface loading, empty, success, and error states.",
                ],
                interfaces=["web app", "API client", "design tokens"],
                scaling_notes=[
                    "Keep frontend state local until cross-page coordination is needed.",
                    "Cache read-heavy API responses at the edge when safe.",
                ],
            )
        )
    if request.include_monitoring:
        components.append(
            ForgeArchitectureComponent(
                name="Observability Layer",
                purpose="Make runtime behavior debuggable in local and production environments.",
                responsibilities=[
                    "Emit structured logs with request and correlation identifiers.",
                    "Track latency, error rate, and dependency health metrics.",
                    "Expose health and readiness probes for deployment automation.",
                ],
                interfaces=["/health", "structured logs", "metrics exporter"],
                scaling_notes=[
                    "Centralize logs before scaling beyond one runtime.",
                    "Add distributed tracing before async workers are introduced.",
                ],
            )
        )
    return ForgeArchitecturePlan(
        summary=(
            f"Build {request.project_name} as a modular {request.application_type} "
            "with typed API contracts, testable domain services, deployment assets, "
            "and observability from day one."
        ),
        principles=[
            "Keep framework adapters thin and domain logic reusable.",
            "Use type-safe schemas for all external boundaries.",
            "Prefer small replaceable modules over one large application object.",
            "Treat tests, Docker, CI, and monitoring as first-class build artifacts.",
        ],
        selected_brain=selected_brain,
        selected_tools=selected_tools,
        components=components,
        data_flow=[
            "Client or automation sends a typed request to the API boundary.",
            "API models validate input and pass commands to the domain service layer.",
            "Services coordinate repositories, external adapters, and policy checks.",
            "Responses are serialized through typed output models.",
            "Logs, metrics, and health probes record the run for operations.",
        ],
        security_model=[
            "Load secrets only from environment variables or secret managers.",
            "Validate every external input at API and service boundaries.",
            "Keep destructive operations behind explicit service methods and tests.",
            "Run dependency and container scans before production promotion.",
        ],
    )


def _folder_structure(
    request: ForgeBuildRequest,
    project_slug: str,
) -> list[ForgeFolderItem]:
    items = [
        _folder(f"{project_slug}/README.md", "Operator and developer guide.", "docs"),
        _folder(f"{project_slug}/.env.example", "Documented runtime settings.", "platform"),
        _folder(f"{project_slug}/backend/app/main.py", "FastAPI application entry.", "backend"),
        _folder(f"{project_slug}/backend/app/api/routes.py", "Versioned API routes.", "backend"),
        _folder(f"{project_slug}/backend/app/core/config.py", "Typed settings.", "backend"),
        _folder(f"{project_slug}/backend/app/services", "Business service modules.", "backend"),
        _folder(f"{project_slug}/backend/app/models", "Pydantic/domain models.", "backend"),
        _folder(f"{project_slug}/tests", "Unit and API tests.", "qa"),
    ]
    if request.include_database:
        items.extend(
            [
                _folder(f"{project_slug}/backend/app/db", "Database adapters.", "backend"),
                _folder(f"{project_slug}/migrations", "Schema migrations.", "backend"),
            ]
        )
    if request.include_frontend:
        items.extend(
            [
                _folder(f"{project_slug}/frontend/src", "Frontend source.", "frontend"),
                _folder(f"{project_slug}/frontend/src/api", "Typed API client.", "frontend"),
                _folder(f"{project_slug}/frontend/src/components", "Reusable UI.", "frontend"),
            ]
        )
    if request.include_docker:
        items.extend(
            [
                _folder(f"{project_slug}/deploy/Dockerfile", "Backend image.", "platform"),
                _folder(
                    f"{project_slug}/deploy/docker-compose.yml",
                    "Local deployment stack.",
                    "platform",
                ),
            ]
        )
    if request.include_ci:
        items.append(
            _folder(
                f"{project_slug}/.github/workflows/ci.yml",
                "Continuous integration pipeline.",
                "platform",
            )
        )
    if request.include_monitoring:
        items.append(
            _folder(
                f"{project_slug}/backend/app/monitoring",
                "Health, metrics, and logging helpers.",
                "platform",
            )
        )
    return items


def _implementation_artifacts(
    request: ForgeBuildRequest,
    project_slug: str,
) -> list[ForgeArtifact]:
    return [
        ForgeArtifact(
            path=f"{project_slug}/backend/app/main.py",
            artifact_type="source",
            purpose="Create the FastAPI app and include API routes.",
            content=_main_py(request.project_name),
        ),
        ForgeArtifact(
            path=f"{project_slug}/backend/app/core/config.py",
            artifact_type="source",
            purpose="Provide typed environment configuration.",
            content=_config_py(request.project_name),
        ),
        ForgeArtifact(
            path=f"{project_slug}/backend/app/api/routes.py",
            artifact_type="source",
            purpose="Expose health and primary execution endpoints.",
            content=_routes_py(request),
        ),
        ForgeArtifact(
            path=f"{project_slug}/backend/app/services/forge_service.py",
            artifact_type="source",
            purpose="Hold the first domain service boundary.",
            content=_service_py(request),
        ),
        ForgeArtifact(
            path=f"{project_slug}/README.md",
            artifact_type="doc",
            purpose="Explain setup, local run, tests, and deployment.",
            content=_readme_md(request),
        ),
        ForgeArtifact(
            path=f"{project_slug}/.env.example",
            artifact_type="config",
            purpose="List required local environment variables.",
            content=_env_example(),
        ),
    ]


def _test_artifacts(
    request: ForgeBuildRequest,
    project_slug: str,
) -> list[ForgeArtifact]:
    return [
        ForgeArtifact(
            path=f"{project_slug}/tests/test_health.py",
            artifact_type="test",
            purpose="Verify health endpoint behavior.",
            content=_health_test_py(),
        ),
        ForgeArtifact(
            path=f"{project_slug}/tests/test_service.py",
            artifact_type="test",
            purpose="Verify domain service output shape and validation behavior.",
            content=_service_test_py(request),
        ),
    ]


def _deployment_setup(
    request: ForgeBuildRequest,
    project_slug: str,
) -> ForgeDeploymentSetup:
    artifacts: list[ForgeArtifact] = []
    if request.include_docker:
        artifacts.extend(
            [
                ForgeArtifact(
                    path=f"{project_slug}/deploy/Dockerfile",
                    artifact_type="docker",
                    purpose="Build a slim Python backend image.",
                    content=_dockerfile(),
                ),
                ForgeArtifact(
                    path=f"{project_slug}/deploy/docker-compose.yml",
                    artifact_type="docker",
                    purpose="Run the app and local services consistently.",
                    content=_docker_compose(request),
                ),
            ]
        )
    if request.include_ci:
        artifacts.append(
            ForgeArtifact(
                path=f"{project_slug}/.github/workflows/ci.yml",
                artifact_type="ci",
                purpose="Run install, tests, and compile checks on push and PR.",
                content=_ci_yml(),
            )
        )
    return ForgeDeploymentSetup(
        target=request.deployment_target,
        artifacts=artifacts,
        environment_variables=[
            "APP_ENV",
            "APP_NAME",
            "LOG_LEVEL",
            "DATABASE_URL" if request.include_database else "STATE_PATH",
        ],
        run_commands=[
            "python3 -m venv .venv",
            "source .venv/bin/activate",
            "pip install -r requirements.txt",
            "uvicorn app.main:app --host 0.0.0.0 --port 8088",
        ],
        release_checks=[
            "python -m pytest",
            "python -m compileall -q backend/app tests",
            "docker compose -f deploy/docker-compose.yml config",
            "curl -f http://localhost:8088/health",
        ],
    )


def _monitoring_setup(request: ForgeBuildRequest) -> ForgeMonitoringSetup:
    if not request.include_monitoring:
        return ForgeMonitoringSetup(
            health_checks=["Provide at least a lightweight /health endpoint."],
            logs=[],
            metrics=[],
            traces=[],
            alerts=[],
        )
    return ForgeMonitoringSetup(
        health_checks=[
            "GET /health returns service status, app name, and environment.",
            "Add /ready when external dependencies become mandatory.",
        ],
        logs=[
            "Emit structured JSON logs with request_id, route, status_code, and duration_ms.",
            "Log validation failures at warning level and unexpected exceptions at error level.",
        ],
        metrics=[
            "Track request count, request latency, error count, and dependency health.",
            "Add per-feature counters for high-value business workflows.",
        ],
        traces=[
            "Wrap external API and database calls with trace spans.",
            "Propagate correlation IDs across workers and downstream calls.",
        ],
        alerts=[
            "Alert when health checks fail for more than two consecutive intervals.",
            "Alert on sustained 5xx error rate, p95 latency, or database connection failures.",
        ],
    )


def _optimization_report(
    request: ForgeBuildRequest,
    selected_brain: str,
    selected_tools: list[str],
    tool_reasoning: list[str],
    security_score: str,
    security_risks: list[str],
) -> list[str]:
    report = [
        f"Forge routed architecture and coding planning to {selected_brain}.",
        f"Recommended build tools: {', '.join(selected_tools) or 'none selected'}.",
        f"Security Sentinel score for the requested construction brief: {security_score}.",
    ]
    report.extend(tool_reasoning[:3])
    if security_risks:
        report.append(
            "Security risks must be resolved before generated artifacts execute in production: "
            + "; ".join(security_risks[:3])
        )
    if request.scalability_target.lower() in {"high", "very_high", "enterprise"}:
        report.append(
            "Prioritize stateless services, queue-backed background work, and database indexes."
        )
    if request.privacy_level.lower() in {"private", "confidential", "restricted"}:
        report.append(
            "Prefer local execution, private package registries, encrypted storage, "
            "and minimal logs."
        )
    if request.include_frontend:
        report.append(
            "Generate API contracts first so frontend clients stay synchronized with backend types."
        )
    report.append(
        "Next recursive improvement step: compare generated artifacts against real test failures "
        "and store successful patterns in SATURNIX neural memory."
    )
    return report


def _folder(path: str, purpose: str, owner: str) -> ForgeFolderItem:
    return ForgeFolderItem(path=path, purpose=purpose, owner=owner)


def _task_type(request: ForgeBuildRequest) -> str:
    parts = [request.application_type, *request.stack, *request.features, request.goal]
    text = " ".join(parts).lower()
    if "frontend" in text and "backend" in text:
        return "fullstack coding architecture"
    if "frontend" in text:
        return "frontend coding architecture"
    if "api" in text or "backend" in text:
        return "backend api coding architecture"
    return "software coding architecture"


def _tool_routing_task(request: ForgeBuildRequest) -> str:
    parts = [
        request.goal,
        request.application_type,
        request.deployment_target,
        *request.stack,
        *request.features,
    ]
    if request.include_docker:
        parts.append("docker container deployment")
    if request.include_ci:
        parts.append("github ci pipeline")
    if request.include_database:
        parts.append("database persistence")
    if request.include_monitoring:
        parts.append("health monitoring logs metrics")
    return " ".join(parts)


def _forge_selected_tools(
    request: ForgeBuildRequest,
    routed_tools: list[str],
) -> list[str]:
    selected = list(routed_tools)
    required = []
    if request.include_docker:
        required.append("docker")
    if request.include_ci:
        required.append("github")
    if request.include_database:
        required.append("databases")
    required.extend(["file_systems", "local_python"])
    for tool in required:
        if tool not in selected:
            selected.append(tool)
    return selected[:6]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "saturnix-forged-system"


def _main_py(project_name: str) -> str:
    return f'''from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings


settings = get_settings()
app = FastAPI(title="{project_name}", version="0.1.0")
app.include_router(router)


@app.get("/health")
async def health():
    return {{
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }}
'''


def _config_py(project_name: str) -> str:
    return f'''from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "{project_name}"
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./app.sqlite3"


@lru_cache
def get_settings() -> Settings:
    return Settings()
'''


def _routes_py(request: ForgeBuildRequest) -> str:
    feature_lines = ", ".join(repr(feature) for feature in request.features)
    return f'''from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.services.forge_service import ForgeService


router = APIRouter(prefix="/v1")


class ExecuteRequest(BaseModel):
    goal: str = Field(min_length=1)
    context: dict = Field(default_factory=dict)


class ExecuteResponse(BaseModel):
    goal: str
    status: str
    features: list[str]
    next_actions: list[str]


@router.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest):
    service = ForgeService(features=[{feature_lines}])
    return service.execute(request.goal, request.context)
'''


def _service_py(request: ForgeBuildRequest) -> str:
    default_actions = [
        "Add repository-specific validation rules.",
        "Connect persistence through a repository interface.",
        "Wire observability before production traffic.",
    ]
    action_lines = "\n".join(f'            "{action}",' for action in default_actions)
    return f'''from __future__ import annotations


class ForgeService:
    """Domain service for {request.project_name}."""

    def __init__(self, features: list[str] | None = None) -> None:
        self.features = features or []

    def execute(self, goal: str, context: dict | None = None) -> dict:
        if not goal.strip():
            raise ValueError("goal is required")
        return {{
            "goal": goal,
            "status": "planned",
            "features": self.features,
            "next_actions": [
{action_lines}
            ],
        }}
'''


def _readme_md(request: ForgeBuildRequest) -> str:
    return f'''# {request.project_name}

Generated by SATURNIX Forge Coding Engine.

## Goal

{request.goal}

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8088
```

## Test

```bash
python -m pytest
python -m compileall -q backend/app tests
```

## Deployment

Use the files under `deploy/` for Docker-based local or server deployment.
Keep secrets in environment variables and never commit `.env`.
'''


def _env_example() -> str:
    return """APP_ENV=local
APP_NAME=saturnix-forged-system
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./app.sqlite3
"""


def _health_test_py() -> str:
    return '''from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
'''


def _service_test_py(request: ForgeBuildRequest) -> str:
    first_feature = request.features[0] if request.features else "core workflow"
    return f'''import pytest

from app.services.forge_service import ForgeService


def test_forge_service_execute_returns_plan():
    result = ForgeService(features=["{first_feature}"]).execute("ship feature")
    assert result["status"] == "planned"
    assert "{first_feature}" in result["features"]
    assert result["next_actions"]


def test_forge_service_rejects_empty_goal():
    with pytest.raises(ValueError):
        ForgeService().execute(" ")
'''


def _dockerfile() -> str:
    return """FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
EXPOSE 8088
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]
"""


def _docker_compose(request: ForgeBuildRequest) -> str:
    service_name = _slugify(request.project_name)
    return f"""services:
  {service_name}:
    build:
      context: ..
      dockerfile: deploy/Dockerfile
    env_file:
      - ../.env
    ports:
      - "8088:8088"
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - import urllib.request; urllib.request.urlopen('http://localhost:8088/health')
      interval: 30s
      timeout: 5s
      retries: 3
"""


def _ci_yml() -> str:
    return """name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install --upgrade pip
      - run: pip install -r requirements.txt
      - run: python -m pytest
      - run: python -m compileall -q backend/app tests
"""
