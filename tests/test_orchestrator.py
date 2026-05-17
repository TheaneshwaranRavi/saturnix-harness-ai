import asyncio

from saturnix_harness.config import Settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.schemas import HarnessRequest


def test_orchestrator_runs_mock_workflow(tmp_path):
    settings = Settings(
        saturnix_env="test",
        saturnix_enable_mock_brains=True,
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
    )
    orchestrator = CoreOrchestrator(settings=settings)

    result = asyncio.run(
        orchestrator.run(
            HarnessRequest(
                goal="Design a multi-agent coding workflow with verification.",
                input="Use OpenAI for planning and local coding model for private snippets.",
            )
        )
    )

    assert result.output
    assert result.intent.domain in {"software", "agentic_systems"}
    assert result.verification.score >= 0
    assert len(result.traces) == 2
    assert result.metadata["recursive_improvement"]["optimization_report"]
    assert result.metadata["recursive_improvement_strategy_ids"]
