from functools import lru_cache

from saturnix_harness.core.orchestrator import CoreOrchestrator


@lru_cache
def get_orchestrator() -> CoreOrchestrator:
    return CoreOrchestrator()

