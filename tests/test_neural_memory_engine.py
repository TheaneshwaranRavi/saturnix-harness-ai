from fastapi.testclient import TestClient

from saturnix_harness.api.dependencies import get_orchestrator
from saturnix_harness.config import Settings
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.main import app
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.memory.neural_engine import NeuralMemoryEngine
from saturnix_harness.schemas import (
    NeuralMemoryCompressionRequest,
    NeuralMemoryRecallRequest,
    NeuralMemoryStoreRequest,
)


def test_neural_memory_store_links_and_recalls_ranked_memories(tmp_path):
    engine = _engine(tmp_path)
    first = engine.store(
        NeuralMemoryStoreRequest(
            content=(
                "Successful FastAPI workflow used security sentinel checks, consensus "
                "review, and verification before execution."
            ),
            category="successful_workflow",
            title="Secure FastAPI workflow",
            importance_score=0.9,
        )
    )
    second = engine.store(
        NeuralMemoryStoreRequest(
            content=(
                "Optimization strategy: reuse security sentinel checks and consensus "
                "review before FastAPI automation execution."
            ),
            category="optimization_strategy",
            title="Security consensus optimization",
            importance_score=0.8,
        )
    )

    assert first.memory.metadata["neural_category"] == "successful_workflow"
    assert second.linked_memory_ids == [first.memory.id]

    recalled = engine.recall(
        NeuralMemoryRecallRequest(
            query="FastAPI security consensus workflow",
            limit=5,
        )
    )

    assert recalled.ranked_memories
    assert recalled.ranked_memories[0].rank_score >= recalled.ranked_memories[-1].rank_score
    assert "Relevant SATURNIX long-term memories" in recalled.context_summary
    assert first.memory.id in recalled.compressed_context
    assert recalled.memory_links
    assert recalled.aging_notes


def test_neural_memory_compresses_namespace(tmp_path):
    engine = _engine(tmp_path)
    engine.store(
        NeuralMemoryStoreRequest(
            content="Project architecture uses brain router, verification, and memory manager.",
            category="project_architecture",
            title="Architecture memory",
        )
    )
    engine.store(
        NeuralMemoryStoreRequest(
            content="Reusable agent structure separates coding, research, and verification.",
            category="reusable_agent_structure",
            title="Agent structure memory",
        )
    )

    compressed = engine.compress(NeuralMemoryCompressionRequest())

    assert compressed.source_record_ids
    assert compressed.summary_record.kind == "compressed_neural_memory"
    assert compressed.compression_ratio > 0
    assert "Category counts" in compressed.summary


def test_neural_memory_api_endpoints(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    try:
        store_response = client.post(
            "/v1/neural-memory/store",
            json={
                "content": "User prefers local Ollama for private code snippets.",
                "category": "user_preference",
                "importance_score": 0.85,
            },
        )
        assert store_response.status_code == 200
        stored = store_response.json()
        assert stored["memory"]["kind"] == "user_preference"

        recall_response = client.post(
            "/v1/neural-memory/recall",
            json={"query": "private code snippets local Ollama", "limit": 3},
        )
        assert recall_response.status_code == 200
        recalled = recall_response.json()
        assert recalled["ranked_memories"]
        assert recalled["context_summary"]

        compress_response = client.post(
            "/v1/neural-memory/compress",
            json={"limit": 10},
        )
        assert compress_response.status_code == 200
        assert compress_response.json()["summary_record"]["kind"] == "compressed_neural_memory"
    finally:
        app.dependency_overrides.clear()


def _engine(tmp_path):
    return NeuralMemoryEngine(MemoryManager(_settings(tmp_path)))


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "neural_memory.sqlite3",
    )
