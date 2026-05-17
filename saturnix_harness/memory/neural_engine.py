from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone

from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.schemas import (
    MemoryRecord,
    MemoryType,
    NeuralMemoryCompressionRequest,
    NeuralMemoryCompressionResult,
    NeuralMemoryHit,
    NeuralMemoryLink,
    NeuralMemoryRecallRequest,
    NeuralMemoryRecallResult,
    NeuralMemoryStoreRequest,
    NeuralMemoryStoreResult,
    SaveMemoryRequest,
    SearchMemoryRequest,
    UpdateMemoryRequest,
)


class NeuralMemoryEngine:
    """Long-term evolving intelligence layer for SATURNIX memory.

    This engine keeps SQLite and vector memory as the storage substrate while
    adding ranking, aging, compression, semantic links, and context summaries.
    """

    def __init__(self, memory: MemoryManager) -> None:
        self.memory = memory

    def store(self, request: NeuralMemoryStoreRequest) -> NeuralMemoryStoreResult:
        compressed_summary = (
            _compress_text(request.content) if request.compress else request.content
        )
        link_query = request.link_query or request.content
        related = self._find_related(
            query=link_query,
            namespace=request.namespace,
            limit=8,
        )
        metadata = {
            **request.metadata,
            "neural_category": request.category,
            "importance_score": request.importance_score,
            "compressed_summary": compressed_summary,
            "original_length": len(request.content),
            "access_count": 0,
            "last_accessed_at": None,
            "neural_links": [],
        }
        record = self.memory.save_memory(
            SaveMemoryRequest(
                content=request.content,
                memory_type=_memory_type_for_category(request.category),
                namespace=request.namespace,
                kind=request.category,
                title=request.title or _title_from_content(request.content),
                tags=_dedupe([*request.tags, "neural_memory", request.category]),
                metadata=metadata,
                source=request.source,
            )
        )
        links = self._link_record(record, related)
        aging_policy = {
            "ranking": "semantic relevance + importance + recency + link strength",
            "half_life_days": 180,
            "compression": "stored compressed_summary alongside full record",
        }
        return NeuralMemoryStoreResult(
            memory=record,
            compressed_summary=compressed_summary,
            linked_memory_ids=[link.target_id for link in links],
            aging_policy=aging_policy,
        )

    def recall(self, request: NeuralMemoryRecallRequest) -> NeuralMemoryRecallResult:
        records = self._candidate_records(request)
        hits = [
            _rank_record(record, request.query, request.half_life_days)
            for record in records
            if _category_matches(record, request.categories)
        ]
        ranked = sorted(hits, key=lambda hit: hit.rank_score, reverse=True)[: request.limit]
        self._record_accesses([hit.memory for hit in ranked])
        links = self._links_for_hits(ranked) if request.include_links else []
        context_summary = _context_summary(ranked) if request.include_summary else ""
        compressed_context = _compressed_context(ranked)
        return NeuralMemoryRecallResult(
            query=request.query,
            ranked_memories=ranked,
            context_summary=context_summary,
            compressed_context=compressed_context,
            memory_links=links,
            aging_notes=_aging_notes(ranked, request.half_life_days),
        )

    def compress(
        self,
        request: NeuralMemoryCompressionRequest,
    ) -> NeuralMemoryCompressionResult:
        records = self.memory.sqlite.list(namespace=request.namespace, limit=request.limit)
        if request.category:
            records = [
                record
                for record in records
                if record.kind == request.category
                or record.metadata.get("neural_category") == request.category
            ]
        summary = _summary_for_records(records)
        source_ids = [record.id for record in records]
        original_size = sum(len(record.content) for record in records) or 1
        ratio = round(min(1.0, len(summary) / original_size), 3)
        summary_record = self.memory.save_memory(
            SaveMemoryRequest(
                content=summary,
                memory_type=MemoryType.project_history,
                namespace=request.namespace,
                kind="compressed_neural_memory",
                title=request.title or "Compressed SATURNIX neural memory",
                tags=["neural_memory", "compressed_summary"],
                metadata={
                    "source_record_ids": source_ids,
                    "source_count": len(source_ids),
                    "compression_ratio": ratio,
                    "neural_category": request.category or "mixed",
                },
                source="neural_memory_engine",
            )
        )
        return NeuralMemoryCompressionResult(
            summary_record=summary_record,
            source_record_ids=source_ids,
            compression_ratio=ratio,
            summary=summary,
        )

    def _candidate_records(self, request: NeuralMemoryRecallRequest) -> list[MemoryRecord]:
        records = self.memory.search_memory(
            SearchMemoryRequest(
                query=request.query,
                namespace=request.namespace,
                tags=request.tags,
                limit=max(request.limit * 3, request.limit),
                include_vector=True,
            )
        )
        if records:
            return records
        return self.memory.sqlite.list(namespace=request.namespace, limit=request.limit * 3)

    def _find_related(
        self,
        query: str,
        namespace: str,
        limit: int,
    ) -> list[MemoryRecord]:
        records = self.memory.search_memory(
            SearchMemoryRequest(
                query=query,
                namespace=namespace,
                tags=["neural_memory"],
                limit=limit,
                include_vector=True,
            )
        )
        return records

    def _link_record(
        self,
        record: MemoryRecord,
        related: list[MemoryRecord],
    ) -> list[NeuralMemoryLink]:
        links: list[NeuralMemoryLink] = []
        source_tokens = _tokens(record.content)
        for target in related:
            if target.id == record.id:
                continue
            strength = _token_similarity(source_tokens, _tokens(target.content))
            if strength < 0.12:
                continue
            relationship = _relationship(record, target)
            links.append(
                NeuralMemoryLink(
                    source_id=record.id,
                    target_id=target.id,
                    relationship=relationship,
                    strength=strength,
                    reason=f"Shared semantic markers for {relationship}.",
                )
            )
        if links:
            self._persist_links(record, links)
            self._persist_reverse_links(record, links)
        return links

    def _persist_links(
        self,
        record: MemoryRecord,
        links: list[NeuralMemoryLink],
    ) -> None:
        metadata = dict(record.metadata)
        metadata["neural_links"] = [link.model_dump(mode="json") for link in links]
        self.memory.update_memory(record.id, UpdateMemoryRequest(metadata=metadata))

    def _persist_reverse_links(
        self,
        record: MemoryRecord,
        links: list[NeuralMemoryLink],
    ) -> None:
        for link in links:
            target = self.memory.sqlite.get(link.target_id)
            if not target:
                continue
            reverse = NeuralMemoryLink(
                source_id=target.id,
                target_id=record.id,
                relationship=link.relationship,
                strength=link.strength,
                reason=f"Linked back from newer memory {record.id}.",
            )
            existing = list(target.metadata.get("neural_links", []))
            if not any(item.get("target_id") == record.id for item in existing):
                existing.append(reverse.model_dump(mode="json"))
            metadata = {**target.metadata, "neural_links": existing}
            self.memory.update_memory(target.id, UpdateMemoryRequest(metadata=metadata))

    def _record_accesses(self, records: list[MemoryRecord]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for record in records:
            metadata = dict(record.metadata)
            metadata["access_count"] = int(metadata.get("access_count") or 0) + 1
            metadata["last_accessed_at"] = now
            self.memory.update_memory(record.id, UpdateMemoryRequest(metadata=metadata))

    def _links_for_hits(self, hits: list[NeuralMemoryHit]) -> list[NeuralMemoryLink]:
        links: list[NeuralMemoryLink] = []
        hit_ids = {hit.memory.id for hit in hits}
        for hit in hits:
            for item in hit.memory.metadata.get("neural_links", []):
                try:
                    link = NeuralMemoryLink.model_validate(item)
                except Exception:
                    continue
                if link.target_id in hit_ids or len(links) < 12:
                    links.append(link)
        return _dedupe_links(links)


def _rank_record(
    record: MemoryRecord,
    query: str,
    half_life_days: int,
) -> NeuralMemoryHit:
    semantic_score = _token_similarity(_tokens(query), _tokens(record.content))
    importance_score = float(record.metadata.get("importance_score") or 0.5)
    age_days = _age_days(record.updated_at)
    recency_score = _recency_score(age_days, half_life_days)
    link_count = len(record.metadata.get("neural_links", []))
    link_score = min(0.15, link_count * 0.03)
    rank = (semantic_score * 0.5) + (importance_score * 0.25) + (recency_score * 0.2)
    rank_score = round(min(1.0, rank + link_score), 3)
    return NeuralMemoryHit(
        memory=record,
        rank_score=rank_score,
        semantic_score=round(semantic_score, 3),
        importance_score=round(importance_score, 3),
        recency_score=round(recency_score, 3),
        age_days=round(age_days, 3),
        linked_memory_ids=[
            item.get("target_id", "")
            for item in record.metadata.get("neural_links", [])
            if item.get("target_id")
        ],
    )


def _memory_type_for_category(category: str) -> MemoryType:
    mapping = {
        "successful_workflow": MemoryType.successful_workflows,
        "failed_workflow": MemoryType.failed_workflows,
        "user_preference": MemoryType.user_preferences,
        "project_architecture": MemoryType.project_history,
        "reasoning_pattern": MemoryType.project_history,
        "optimization_strategy": MemoryType.project_history,
        "code_snippet": MemoryType.code_snippets,
        "reusable_agent_structure": MemoryType.project_history,
    }
    return mapping.get(category, MemoryType.project_history)


def _category_matches(record: MemoryRecord, categories: list[str]) -> bool:
    if not categories:
        return True
    category = record.metadata.get("neural_category") or record.kind
    return category in categories


def _relationship(source: MemoryRecord, target: MemoryRecord) -> str:
    source_category = source.metadata.get("neural_category") or source.kind
    target_category = target.metadata.get("neural_category") or target.kind
    if source_category == target_category:
        return f"same_category:{source_category}"
    return f"{source_category}->supports->{target_category}"


def _compress_text(text: str, max_sentences: int = 4) -> str:
    cleaned = " ".join(text.split())
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    if len(cleaned) <= 700:
        return cleaned
    selected = sentences[:max_sentences]
    summary = " ".join(selected)
    if len(summary) > 700:
        summary = summary[:697].rstrip() + "..."
    return summary


def _context_summary(hits: list[NeuralMemoryHit]) -> str:
    if not hits:
        return "No neural memories matched the query."
    lines = ["Relevant SATURNIX long-term memories:"]
    for hit in hits[:6]:
        category = hit.memory.metadata.get("neural_category") or hit.memory.kind
        summary = hit.memory.metadata.get("compressed_summary") or _compress_text(
            hit.memory.content
        )
        lines.append(
            f"- [{category} score={hit.rank_score}] {hit.memory.title}: {summary}"
        )
    return "\n".join(lines)


def _compressed_context(hits: list[NeuralMemoryHit]) -> str:
    parts: list[str] = []
    for hit in hits[:8]:
        summary = hit.memory.metadata.get("compressed_summary") or _compress_text(
            hit.memory.content
        )
        parts.append(f"{hit.memory.id}: {summary}")
    return "\n".join(parts)


def _summary_for_records(records: list[MemoryRecord]) -> str:
    if not records:
        return "No neural memories available for compression."
    grouped = Counter(record.metadata.get("neural_category") or record.kind for record in records)
    lines = [
        "Compressed SATURNIX neural memory summary.",
        "Category counts: "
        + ", ".join(f"{category}: {count}" for category, count in sorted(grouped.items())),
        "Durable lessons:",
    ]
    for record in records[:12]:
        summary = record.metadata.get("compressed_summary") or _compress_text(record.content)
        category = record.metadata.get("neural_category") or record.kind
        lines.append(f"- {category}: {summary}")
    return "\n".join(lines)


def _aging_notes(hits: list[NeuralMemoryHit], half_life_days: int) -> list[str]:
    notes = [f"Aging half-life: {half_life_days} days."]
    old = [hit for hit in hits if hit.age_days > half_life_days and hit.importance_score < 0.5]
    if old:
        notes.append("Low-importance older memories should be compressed or reviewed.")
    if any(hit.importance_score >= 0.8 for hit in hits):
        notes.append("High-importance memories retained strongly despite age.")
    return notes


def _title_from_content(content: str) -> str:
    title = " ".join(content.strip().split())[:80]
    return title or "SATURNIX neural memory"


def _tokens(text: str) -> set[str]:
    stopwords = {
        "the",
        "and",
        "that",
        "with",
        "from",
        "into",
        "this",
        "should",
        "would",
        "could",
        "saturnix",
        "memory",
    }
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", text.lower())
        if token not in stopwords
    }


def _token_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / len(left.union(right))


def _age_days(value: datetime) -> float:
    now = datetime.now(timezone.utc)
    timestamp = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return max(0.0, (now - timestamp).total_seconds() / 86400)


def _recency_score(age_days: float, half_life_days: int) -> float:
    return math.pow(0.5, age_days / half_life_days)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _dedupe_links(links: list[NeuralMemoryLink]) -> list[NeuralMemoryLink]:
    seen: set[tuple[str, str, str]] = set()
    result: list[NeuralMemoryLink] = []
    for link in links:
        key = (link.source_id, link.target_id, link.relationship)
        if key in seen:
            continue
        seen.add(key)
        result.append(link)
    return result
