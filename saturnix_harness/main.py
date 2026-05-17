from fastapi import FastAPI

from saturnix_harness.api.routes import phase1_router, router
from saturnix_harness.config import get_settings
from saturnix_harness.monitoring.logging_config import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    app = FastAPI(
        title="SATURNIX-HARNESS",
        version="0.1.0",
        description="Agentic AI construction framework for multi-brain routing and verified execution.",
    )
    app.include_router(phase1_router)
    app.include_router(router)
    return app


app = create_app()
