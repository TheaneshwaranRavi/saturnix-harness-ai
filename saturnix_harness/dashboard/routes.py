from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile

from saturnix_harness.api.dependencies import get_orchestrator
from saturnix_harness.config import get_settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.dashboard.security import dashboard_identity
from saturnix_harness.dashboard.service import DashboardService
from saturnix_harness.schemas import (
    ApiKeyStoreRequest,
    BrainRouteRequest,
    CreateDashboardAgentRequest,
    DashboardMemorySaveRequest,
    DashboardMemorySearchRequest,
    DashboardSecurityScanRequest,
    DashboardWorkflowRunRequest,
    DataGuardianClassifyRequest,
    ExecuteDashboardAgentRequest,
)

dashboard_router = APIRouter(tags=["SATURNIX Dashboard"])


def get_dashboard_service(
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
) -> DashboardService:
    return DashboardService(orchestrator)


def require_dashboard_identity(authorization: str | None = Header(default=None)):
    return dashboard_identity(get_settings(), authorization=authorization)


@dashboard_router.get("/dashboard/overview")
async def dashboard_overview(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return await service.overview()


@dashboard_router.get("/agents")
async def list_dashboard_agents(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.agents()


@dashboard_router.post("/agents/create")
async def create_dashboard_agent(
    request: CreateDashboardAgentRequest,
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.create_agent(request)


@dashboard_router.post("/agents/execute")
async def execute_dashboard_agent(
    request: ExecuteDashboardAgentRequest,
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return await service.execute_agent(request)


@dashboard_router.get("/brains")
async def dashboard_brains(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return await service.brains()


@dashboard_router.post("/brains/route")
async def dashboard_route_brain(
    request: BrainRouteRequest,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return orchestrator.brain_router.route_task(request)


@dashboard_router.get("/memory")
async def dashboard_memory(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.memory()


@dashboard_router.post("/memory/save")
async def dashboard_save_memory(
    request: DashboardMemorySaveRequest,
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.save_memory(request)


@dashboard_router.post("/memory/search")
async def dashboard_search_memory(
    request: DashboardMemorySearchRequest,
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.search_memory(request)


@dashboard_router.get("/security/status")
async def dashboard_security_status(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.security_status()


@dashboard_router.get("/security/audit-logs")
async def dashboard_audit_logs(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.audit_logs()


@dashboard_router.post("/security/scan-input")
async def dashboard_scan_input(
    request: DashboardSecurityScanRequest,
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.scan_input(request)


@dashboard_router.post("/security/lockdown")
async def dashboard_lockdown(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="ADMIN_SECURITY role is required.")
    return service.lockdown()


@dashboard_router.get("/edge/pi/status")
async def dashboard_edge_status(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.edge_status()


@dashboard_router.get("/storage/status")
async def dashboard_storage_status(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.storage_status()


@dashboard_router.get("/workflows")
async def dashboard_workflows(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.workflows()


@dashboard_router.post("/workflows/run")
async def dashboard_run_workflow(
    request: DashboardWorkflowRunRequest,
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return await service.run_workflow(request)


@dashboard_router.get("/voice/status")
async def dashboard_voice_status(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.voice_status()


@dashboard_router.post("/voice/transcribe")
async def dashboard_voice_transcribe(
    file: UploadFile,
    orchestrator: CoreOrchestrator = Depends(get_orchestrator),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    try:
        content = await file.read()
        return await orchestrator.voice_engine.transcribe_bytes(
            content,
            filename=file.filename or "audio.wav",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@dashboard_router.get("/logs")
async def dashboard_logs(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.logs()


@dashboard_router.get("/api-keys")
async def dashboard_api_keys(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.api_keys()


@dashboard_router.post("/api-keys/store")
async def dashboard_store_api_key(
    request: ApiKeyStoreRequest,
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="ADMIN_SECURITY role is required.")
    return service.store_api_key(request)


@dashboard_router.get("/profile")
async def dashboard_profile(
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.user_profile()


@dashboard_router.post("/data/classify")
async def dashboard_classify_data(
    request: DataGuardianClassifyRequest,
    service: DashboardService = Depends(get_dashboard_service),
    identity: dict = Depends(require_dashboard_identity),
):
    _ = identity
    return service.data_guardian.classify(request)
