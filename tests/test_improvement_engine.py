from saturnix_harness.config import Settings
from saturnix_harness.core.improvement_engine import RecursiveImprovementEngine
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.schemas import SaturnixExecutionResult, SearchMemoryRequest


def test_recursive_improvement_engine_generates_and_stores_report(tmp_path):
    memory = MemoryManager(_settings(tmp_path))
    engine = RecursiveImprovementEngine(memory)

    result = SaturnixExecutionResult(
        goal="Build private coding workflow with verification",
        detected_intent="private coding workflow",
        agents_used=["coding_agent"],
        brain_routing={"selected_brain": "GPT", "fallback_brain": "Claude"},
        workflow=[
            {"name": "Execute", "prompt": "Build private coding workflow"},
        ],
        execution_result={
            "ok": False,
            "output": "This is guaranteed to always work according to sources.",
            "traces": [
                {
                    "step_id": "1",
                    "step_name": "Execute",
                    "ok": False,
                    "error": "tool unavailable",
                }
            ],
        },
        validation_result={
            "ok": False,
            "score": 0.4,
            "findings": ["Hallucination risk: unsupported claim"],
        },
        memory_saved={},
        next_actions=[],
    )

    report = engine.analyze_execution(result)

    assert report.optimization_report
    assert report.architecture_improvements
    assert report.prompt_upgrades
    assert report.routing_improvements
    assert report.execution_improvements
    assert report.memory_improvements
    assert report.agent_coordination_improvements
    assert report.detected_failures
    assert report.detected_hallucinations
    assert report.detected_weak_workflows
    assert report.stored_strategy_ids

    stored = memory.search_memory(
        SearchMemoryRequest(
            query="optimization",
            namespace="saturnix:optimization",
            limit=10,
            include_vector=False,
        )
    )
    assert stored
    assert all(record.kind == "optimization_strategy" for record in stored)


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
    )
