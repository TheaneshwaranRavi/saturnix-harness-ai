from fastapi.testclient import TestClient

from saturnix_harness.api.dependencies import get_orchestrator
from saturnix_harness.config import Settings
from saturnix_harness.core.distributed_intelligence import DistributedIntelligenceEngine
from saturnix_harness.core.orchestrator import CoreOrchestrator
from saturnix_harness.main import app
from saturnix_harness.schemas import DistributedIntelligenceRequest


def test_distributed_intelligence_assigns_all_required_nodes():
    result = DistributedIntelligenceEngine().plan(
        DistributedIntelligenceRequest(
            workloads=[
                "centralized orchestration and brain routing",
                "edge automation for Raspberry Pi sensors",
                "memory vault synchronization",
                "cloud large context analysis",
            ],
            privacy_level="standard",
            latency_priority="high",
        )
    )

    nodes = {assignment.node for assignment in result.node_assignments}
    assert nodes == {"MacBook M1", "Raspberry Pi", "External Storage", "Cloud APIs"}
    assert any("orchestration" in item for item in _workloads(result, "MacBook M1"))
    assert any("edge automation" in item for item in _workloads(result, "Raspberry Pi"))
    assert any("memory vault" in item for item in _workloads(result, "External Storage"))
    assert any("cloud large context" in item for item in _workloads(result, "Cloud APIs"))
    assert result.optimization_plan
    assert result.failover_strategy


def test_distributed_intelligence_handles_private_cloud_and_degraded_nodes():
    result = DistributedIntelligenceEngine().plan(
        DistributedIntelligenceRequest(
            privacy_level="private",
            latency_priority="low_latency",
            node_health={"Raspberry Pi": "degraded"},
        )
    )

    raspberry = next(
        assignment for assignment in result.node_assignments if assignment.node == "Raspberry Pi"
    )
    cloud_usage = next(usage for usage in result.resource_usage if usage.node == "Cloud APIs")

    assert any("standby only" in item for item in raspberry.assigned_workloads)
    assert any("redact" in item.lower() for item in result.optimization_plan)
    assert any("redacted" in item.lower() for item in cloud_usage.constraints)
    assert any("destructive" in item.lower() for item in result.failover_strategy)


def test_distributed_intelligence_api_endpoint(tmp_path):
    orchestrator = CoreOrchestrator(settings=_settings(tmp_path))

    app.dependency_overrides[get_orchestrator] = lambda: orchestrator
    client = TestClient(app)
    try:
        response = client.post(
            "/v1/distributed/plan",
            json={
                "mission": "Coordinate SATURNIX home lab nodes",
                "workloads": [
                    "MacBook orchestration",
                    "Raspberry Pi edge automation",
                    "External storage memory backup",
                ],
                "include_cloud_apis": False,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {
            "node_assignments",
            "resource_usage",
            "optimization_plan",
            "failover_strategy",
        }
        assert {item["node"] for item in payload["node_assignments"]} == {
            "MacBook M1",
            "Raspberry Pi",
            "External Storage",
        }
        assert all(item["node"] != "Cloud APIs" for item in payload["resource_usage"])
    finally:
        app.dependency_overrides.clear()


def _workloads(result, node: str) -> list[str]:
    return next(
        assignment.assigned_workloads
        for assignment in result.node_assignments
        if assignment.node == node
    )


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_enable_mock_brains=True,
        saturnix_enable_chroma=False,
        saturnix_sqlite_path=tmp_path / "distributed.sqlite3",
    )
