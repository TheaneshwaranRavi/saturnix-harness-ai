from __future__ import annotations

import hashlib
from pathlib import Path

from saturnix_harness.memory.base import MemoryStore
from saturnix_harness.schemas import MemoryRecord


def deterministic_embedding(text: str, dimensions: int = 64) -> list[float]:
    """Small local embedding substitute for bootstrapping Chroma without downloads."""

    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    while len(values) < dimensions:
        for byte in digest:
            values.append((byte / 127.5) - 1.0)
            if len(values) == dimensions:
                break
        digest = hashlib.sha256(digest).digest()
    return values


class InMemoryVectorStore(MemoryStore):
    def __init__(self) -> None:
        self.records: list[MemoryRecord] = []

    def add(self, record: MemoryRecord) -> MemoryRecord:
        self.records = [existing for existing in self.records if existing.id != record.id]
        self.records.append(record)
        return record

    def search(self, query: str, namespace: str = "default", limit: int = 5) -> list[MemoryRecord]:
        query_words = set(query.lower().split())
        scored: list[tuple[int, MemoryRecord]] = []
        for record in self.records:
            if record.namespace != namespace:
                continue
            content_words = set(record.content.lower().split())
            score = len(query_words.intersection(content_words))
            if score > 0 or query.lower() in record.content.lower():
                scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:limit]]

    def list(self, namespace: str = "default", limit: int = 50) -> list[MemoryRecord]:
        return [record for record in reversed(self.records) if record.namespace == namespace][:limit]

    def get(self, record_id: str) -> MemoryRecord | None:
        return next((record for record in self.records if record.id == record_id), None)

    def delete(self, record_id: str) -> bool:
        original_count = len(self.records)
        self.records = [record for record in self.records if record.id != record_id]
        return len(self.records) != original_count


class ChromaVectorStore(MemoryStore):
    """ChromaDB vector memory adapter with deterministic local embeddings."""

    def __init__(self, path: Path, collection_name: str = "saturnix_memory") -> None:
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        try:
            import chromadb
        except Exception as exc:  # pragma: no cover - depends on optional dependency
            raise RuntimeError("chromadb is not installed") from exc
        self.client = chromadb.PersistentClient(path=str(path))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "SATURNIX-HARNESS vector memory"},
            embedding_function=None,
        )

    def add(self, record: MemoryRecord) -> MemoryRecord:
        self.collection.upsert(
            ids=[record.id],
            documents=[record.content],
            metadatas=[
                {
                    "namespace": record.namespace,
                    "memory_type": record.memory_type.value,
                    "kind": record.kind,
                    "title": record.title or "",
                    "tags": ",".join(record.tags),
                    "source": record.source or "",
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat(),
                    **{f"meta_{key}": str(value) for key, value in record.metadata.items()},
                }
            ],
            embeddings=[deterministic_embedding(record.content)],
        )
        return record

    def search(self, query: str, namespace: str = "default", limit: int = 5) -> list[MemoryRecord]:
        results = self.collection.query(
            query_embeddings=[deterministic_embedding(query)],
            n_results=limit,
            where={"namespace": namespace},
        )
        records: list[MemoryRecord] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        for record_id, document, metadata in zip(ids, documents, metadatas, strict=False):
            cleaned_metadata = {
                key.removeprefix("meta_"): value
                for key, value in metadata.items()
                if key.startswith("meta_")
            }
            records.append(
                MemoryRecord(
                    id=record_id,
                    namespace=metadata.get("namespace", namespace),
                    memory_type=metadata.get("memory_type", "vector_memory"),
                    kind=metadata.get("kind", "note"),
                    title=metadata.get("title") or None,
                    content=document or "",
                    tags=_split_tags(metadata.get("tags", "")),
                    metadata=cleaned_metadata,
                    source=metadata.get("source") or None,
                    created_at=metadata.get("created_at"),
                    updated_at=metadata.get("updated_at") or metadata.get("created_at"),
                )
            )
        return records

    def list(self, namespace: str = "default", limit: int = 50) -> list[MemoryRecord]:
        results = self.collection.get(where={"namespace": namespace}, limit=limit)
        records: list[MemoryRecord] = []
        for record_id, document, metadata in zip(
            results.get("ids", []),
            results.get("documents", []),
            results.get("metadatas", []),
            strict=False,
        ):
            records.append(
                MemoryRecord(
                    id=record_id,
                    namespace=metadata.get("namespace", namespace),
                    memory_type=metadata.get("memory_type", "vector_memory"),
                    kind=metadata.get("kind", "note"),
                    title=metadata.get("title") or None,
                    content=document or "",
                    tags=_split_tags(metadata.get("tags", "")),
                    metadata={
                        key.removeprefix("meta_"): value
                        for key, value in metadata.items()
                        if key.startswith("meta_")
                    },
                    source=metadata.get("source") or None,
                    created_at=metadata.get("created_at"),
                    updated_at=metadata.get("updated_at") or metadata.get("created_at"),
                )
            )
        return records

    def get(self, record_id: str) -> MemoryRecord | None:
        result = self.collection.get(ids=[record_id])
        ids = result.get("ids", [])
        if not ids:
            return None
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        metadata = metadatas[0] if metadatas else {}
        return MemoryRecord(
            id=ids[0],
            namespace=metadata.get("namespace", "default"),
            memory_type=metadata.get("memory_type", "vector_memory"),
            kind=metadata.get("kind", "note"),
            title=metadata.get("title") or None,
            content=documents[0] if documents else "",
            tags=_split_tags(metadata.get("tags", "")),
            metadata={
                key.removeprefix("meta_"): value
                for key, value in metadata.items()
                if key.startswith("meta_")
            },
            source=metadata.get("source") or None,
            created_at=metadata.get("created_at"),
            updated_at=metadata.get("updated_at") or metadata.get("created_at"),
        )

    def delete(self, record_id: str) -> bool:
        exists = self.get(record_id) is not None
        if exists:
            self.collection.delete(ids=[record_id])
        return exists


def _split_tags(value: str) -> list[str]:
    return [tag for tag in value.split(",") if tag]
