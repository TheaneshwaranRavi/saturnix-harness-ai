from saturnix_harness.config import Settings
from saturnix_harness.memory.manager import MemoryManager
from saturnix_harness.schemas import MemoryType, SaveMemoryRequest, SearchMemoryRequest, UpdateMemoryRequest


def test_memory_persists_and_recalls(tmp_path):
    settings = Settings(
        saturnix_env="test",
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
        saturnix_enable_chroma=False,
    )
    memory = MemoryManager(settings)

    memory.remember("Claude handles long context documents.", namespace="test", kind="fact")
    hits = memory.recall("long context", namespace="test")

    assert hits
    assert hits[0].namespace == "test"
    assert "Claude" in hits[0].content


def test_memory_manager_crud_and_summary(tmp_path):
    memory = MemoryManager(_settings(tmp_path))

    saved = memory.save_memory(
        SaveMemoryRequest(
            content="User prefers concise architecture summaries.",
            memory_type=MemoryType.user_preferences,
            namespace="saturnix",
            kind="preference",
            title="Concise summaries",
            tags=["style", "architecture"],
            metadata={"confidence": "high"},
            source="test",
        )
    )

    assert saved.id
    assert saved.memory_type == MemoryType.user_preferences

    hits = memory.search_memory(
        SearchMemoryRequest(
            query="concise architecture",
            namespace="saturnix",
            memory_type=MemoryType.user_preferences,
            tags=["style"],
        )
    )
    assert [hit.id for hit in hits] == [saved.id]

    updated = memory.update_memory(
        saved.id,
        UpdateMemoryRequest(
            content="User prefers concise technical architecture summaries.",
            tags=["style", "architecture", "technical"],
        ),
    )
    assert updated is not None
    assert "technical" in updated.content
    assert "technical" in updated.tags

    summary = memory.summarize_memory(namespace="saturnix")
    assert summary.total_records == 1
    assert summary.type_counts[MemoryType.user_preferences.value] == 1
    assert "user_preferences" in summary.summary

    result = memory.delete_memory(saved.id)
    assert result.deleted is True
    assert memory.search_memory(SearchMemoryRequest(query="technical", namespace="saturnix")) == []


def test_memory_manager_supports_required_memory_types(tmp_path):
    memory = MemoryManager(_settings(tmp_path))

    for memory_type in MemoryType:
        memory.save_memory(
            SaveMemoryRequest(
                content=f"Example for {memory_type.value}",
                memory_type=memory_type,
                namespace="types",
                kind="example",
            )
        )

    summary = memory.summarize_memory(namespace="types")
    assert summary.total_records == len(MemoryType)
    for memory_type in MemoryType:
        assert summary.type_counts[memory_type.value] == 1


def _settings(tmp_path):
    return Settings(
        saturnix_env="test",
        saturnix_sqlite_path=tmp_path / "memory.sqlite3",
        saturnix_enable_chroma=False,
    )
