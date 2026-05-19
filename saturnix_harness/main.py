from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from saturnix_harness.api.routes import phase1_router, router
from saturnix_harness.config import get_settings
from saturnix_harness.dashboard.routes import dashboard_router
from saturnix_harness.dashboard.security import RateLimitMiddleware, SecurityHeadersMiddleware
from saturnix_harness.monitoring.logging_config import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    app = FastAPI(
        title="SATURNIX-HARNESS",
        version="0.1.0",
        description=(
            "Agentic AI construction framework for multi-brain routing "
            "and verified execution."
        ),
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in settings.saturnix_cors_origins.split(",")
            if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(dashboard_router)
    app.include_router(phase1_router)
    app.include_router(router)
    return app


app = create_app()
