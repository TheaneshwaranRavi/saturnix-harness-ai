import asyncio

from saturnix_harness.brains.base import BrainProvider
from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.config import Settings
from saturnix_harness.core.consensus_engine import ConsensusEngine
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.schemas import (
    BrainName,
    BrainRequest,
    BrainResponse,
    Capability,
    ConsensusRequest,
)


def test_consensus_engine_merges_multiple_brain_outputs(tmp_path):
    engine = ConsensusEngine(
        BrainRouter(
            _settings(tmp_path),
            providers=[
                _StaticProvider(
                    BrainName.openai,
                    "gpt-test",
                    "Use explicit schemas. Verify tool calls before execution.",
                ),
                _StaticProvider(
                    BrainName.claude,
                    "claude-test",
                    "Use explicit schemas. Verify tool calls and document assumptions.",
                ),
                _StaticProvider(
                    BrainName.gemini,
                    "gemini-test",
                    "Use explicit schemas. Return validated JSON for tool calls.",
                ),
                _StaticProvider(
                    BrainName.ollama_gemma,
                    "gemma-test",
                    "Use explicit schemas. Keep private context local when required.",
                ),
            ],
        )
    )

    result = asyncio.run(
        engine.run_consensus(
            ConsensusRequest(
                task="Design a schema-safe tool calling workflow",
                output_format="markdown",
            )
        )
    )

    assert result.consensus_result
    assert len(result.brain_comparisons) == 4
    assert result.confidence_score > 0.4
    assert result.detected_conflicts == []
    assert "highest-confidence output" in result.final_reasoning


def test_consensus_engine_detects_brain_conflicts(tmp_path):
    engine = ConsensusEngine(
        BrainRouter(
            _settings(tmp_path),
            providers=[
                _StaticProvider(
                    BrainName.openai,
                    "gpt-test",
                    "Use local Ollama models for private customer data.",
                ),
                _StaticProvider(
                    BrainName.claude,
                    "claude-test",
                    "Do not use local Ollama models for private customer data.",
                ),
            ],
        )
    )

    result = asyncio.run(
        engine.run_consensus(
            ConsensusRequest(
                task="Choose routing for private customer data",
                privacy_level="private",
                min_brains=2,
            )
        )
    )

    assert result.detected_conflicts
    assert result.confidence_score < 0.7
    assert any(comparison.contradictions for comparison in result.brain_comparisons)


def test_orchestrator_exposes_consensus_engine(tmp_path):
    orchestrator = CoreOrchestrator(
        settings=_settings(tmp_path),
        brain_router=BrainRouter(
            _settings(tmp_path),
            providers=[
                _StaticProvider(
                    BrainName.openai,
                    "gpt-test",
                    "Use verification gates. Record assumptions.",
                ),
                _StaticProvider(
                    BrainName.claude,
                    "claude-test",
                    "Use verification gates. Record assumptions and caveats.",
                ),
            ],
        ),
    )

    result = asyncio.run(
        orchestrator.run_consensus(
            ConsensusRequest(task="Reduce hallucinations in SATURNIX outputs")
        )
    )

    assert result.consensus_result
    assert len(result.brain_comparisons) == 2


class _StaticProvider(BrainProvider):
    capabilities = {Capability.reasoning, Capability.verification}

    def __init__(self, name: BrainName, model: str, content: str) -> None:
        self.name = name
        self.content = content
        super().__init__(model=model, enabled=True)

    async def complete(self, request: BrainRequest) -> BrainResponse:
        return BrainResponse(provider=self.name, model=self.model, content=self.content)


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
    )
