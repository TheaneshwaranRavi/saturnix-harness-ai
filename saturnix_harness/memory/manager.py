from __future__ import annotations

import logging

from saturnix_harness.config import Settings
from saturnix_harness.memory.sqlite_store import SQLiteMemoryStore
from saturnix_harness.memory.vector_store import ChromaVectorStore, InMemoryVectorStore
from saturnix_harness.schemas import (
    DeleteMemoryResult,
    MemoryRecord,
    MemorySummary,
    MemoryType,
    SaveMemoryRequest,
    SearchMemoryRequest,
    UpdateMemoryRequest,
)

logger = logging.getLogger(__name__)


class MemoryManager:
    """System memory and scaling layer.

    SQLite is the source of truth for starter persistence. ChromaDB is used for
    semantic retrieval when installed and enabled; otherwise the framework keeps
    a local in-memory vector-style fallback for development and tests.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.sqlite = SQLiteMemoryStore(settings.sqlite_path)
        self.vector = self._build_vector_store()

    def _build_vector_store(self):
        if not self.settings.saturnix_enable_chroma:
            return InMemoryVectorStore()
        try:
            return ChromaVectorStore(self.settings.chroma_path)
        except Exception as exc:  # pragma: no cover - depends on optional dependency
            logger.warning("ChromaDB unavailable, using in-memory vector fallback: %s", exc)
            return InMemoryVectorStore()

    def remember(
        self,
        content: str,
        namespace: str = "default",
        kind: str = "note",
        metadata: dict | None = None,
    ) -> MemoryRecord:
        return self.save_memory(
            SaveMemoryRequest(
                content=content,
                namespace=namespace,
                kind=kind,
                metadata=metadata or {},
            )
        )

    def save_memory(self, request: SaveMemoryRequest) -> MemoryRecord:
        record = MemoryRecord(
            namespace=request.namespace,
            memory_type=request.memory_type,
            kind=request.kind,
            title=request.title,
            content=request.content,
            tags=request.tags,
            metadata=request.metadata,
            source=request.source,
        )
        self.sqlite.add(record)
        self.vector.add(record)
        logger.info(
            "Saved SATURNIX memory record %s type=%s namespace=%s",
            record.id,
            record.memory_type.value,
            record.namespace,
        )
        return record

    def recall(self, query: str, namespace: str = "default", limit: int = 5) -> list[MemoryRecord]:
        return self.search_memory(SearchMemoryRequest(query=query, namespace=namespace, limit=limit))

    def search_memory(self, request: SearchMemoryRequest) -> list[MemoryRecord]:
        vector_hits: list[MemoryRecord] = []
        if request.include_vector and request.query:
            vector_namespace = request.namespace or "default"
            vector_hits = self.vector.search(
                request.query,
                namespace=vector_namespace,
                limit=request.limit,
            )
            vector_hits = _filter_records(
                vector_hits,
                namespace=request.namespace,
                memory_type=request.memory_type,
                tags=request.tags,
            )
        if vector_hits:
            return vector_hits[: request.limit]
        return self.sqlite.search(
            request.query,
            namespace=request.namespace,
            limit=request.limit,
            memory_type=request.memory_type,
            tags=request.tags,
        )

    def update_memory(self, record_id: str, request: UpdateMemoryRequest) -> MemoryRecord | None:
        record = self.sqlite.update(record_id, request)
        if not record:
            return None
        self.vector.add(record)
        logger.info("Updated SATURNIX memory record %s", record_id)
        return record

    def delete_memory(self, record_id: str) -> DeleteMemoryResult:
        deleted = self.sqlite.delete(record_id)
        self.vector.delete(record_id)
        if deleted:
            logger.info("Deleted SATURNIX memory record %s", record_id)
        return DeleteMemoryResult(id=record_id, deleted=deleted)

    def summarize_memory(
        self,
        namespace: str | None = None,
        memory_type: MemoryType | None = None,
        limit: int = 20,
    ) -> MemorySummary:
        records = self.sqlite.list(namespace=namespace, limit=limit, memory_type=memory_type)
        type_counts = self.sqlite.counts_by_type(namespace=namespace, memory_type=memory_type)
        total_records = sum(type_counts.values())
        summary = _build_memory_summary(records, type_counts)
        return MemorySummary(
            namespace=namespace,
            memory_type=memory_type,
            total_records=total_records,
            type_counts=type_counts,
            recent_records=records,
            summary=summary,
        )

    def list(self, namespace: str = "default", limit: int = 50) -> list[MemoryRecord]:
        return self.sqlite.list(namespace=namespace, limit=limit)

    def save_phase1_execution(
        self,
        goal: str,
        detected_intent: str,
        agents_used: list[str],
        brain_routing: dict,
        workflow: list[dict],
        execution_result: dict,
        validation_result: dict,
    ) -> dict:
        goal_id = self.sqlite.save_user_goal(
            goal=goal,
            detected_intent=detected_intent,
            metadata={"workflow_step_count": len(workflow)},
        )
        brain_route_id = self.sqlite.save_brain_route(
            goal_id=goal_id,
            selected_brain=str(brain_routing.get("selected_brain", "")),
            fallback_brain=brain_routing.get("fallback_brain"),
            reason=brain_routing.get("reason"),
            execution_strategy=brain_routing.get("execution_strategy"),
            metadata=brain_routing,
        )
        agent_run_ids = [
            self.sqlite.save_agent_run(
                goal_id=goal_id,
                agent_name=agent_name,
                status="ok" if execution_result.get("ok") else "failed",
                output=str(execution_result.get("output", "")),
                metadata={"execution_ok": execution_result.get("ok", False)},
            )
            for agent_name in agents_used
        ]
        verification_id = self.sqlite.save_verification_result(
            goal_id=goal_id,
            ok=bool(validation_result.get("ok", False)),
            score=float(validation_result.get("score", 0.0)),
            findings=[str(finding) for finding in validation_result.get("findings", [])],
            improved_output=validation_result.get("improved_output"),
            metadata=validation_result,
        )
        return {
            "user_goal_id": goal_id,
            "agent_run_ids": agent_run_ids,
            "brain_route_id": brain_route_id,
            "verification_result_id": verification_id,
        }

    def phase1_table_counts(self) -> dict[str, int]:
        return self.sqlite.phase1_table_counts()


def _filter_records(
    records: list[MemoryRecord],
    namespace: str | None = None,
    memory_type: MemoryType | None = None,
    tags: list[str] | None = None,
) -> list[MemoryRecord]:
    filtered = records
    if namespace:
        filtered = [record for record in filtered if record.namespace == namespace]
    if memory_type:
        filtered = [record for record in filtered if record.memory_type == memory_type]
    for tag in tags or []:
        filtered = [record for record in filtered if tag in record.tags]
    return filtered


def _build_memory_summary(records: list[MemoryRecord], type_counts: dict[str, int]) -> str:
    if not records:
        return "No SATURNIX memory records matched the requested filters."
    type_text = ", ".join(f"{memory_type}: {count}" for memory_type, count in sorted(type_counts.items()))
    recent_titles = [
        record.title or record.content[:80].replace("\n", " ")
        for record in records[:5]
    ]
    recent_text = "; ".join(recent_titles)
    return (
        f"Memory contains {sum(type_counts.values())} records"
        f" across {len(type_counts)} type(s): {type_text}. "
        f"Most recent relevant records: {recent_text}."
    )
