from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from saturnix_harness.memory.base import MemoryStore
from saturnix_harness.schemas import MemoryRecord, MemoryType, UpdateMemoryRequest


class SQLiteMemoryStore(MemoryStore):
    """Starter durable memory using SQLite."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_records (
                    id TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL,
                    memory_type TEXT NOT NULL DEFAULT 'vector_memory',
                    kind TEXT NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]',
                    metadata TEXT NOT NULL,
                    source TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT ''
                )
                """
            )
            self._ensure_columns(connection)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_namespace ON memory_records(namespace)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_kind ON memory_records(kind)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_records(memory_type)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_updated_at ON memory_records(updated_at)"
            )
            self._init_phase1_tables(connection)

    def _init_phase1_tables(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_goals (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                detected_intent TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_runs (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                status TEXT NOT NULL,
                output TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(goal_id) REFERENCES user_goals(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS brain_routes (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                selected_brain TEXT NOT NULL,
                fallback_brain TEXT,
                reason TEXT,
                execution_strategy TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(goal_id) REFERENCES user_goals(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS verification_results (
                id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                ok INTEGER NOT NULL,
                score REAL NOT NULL,
                findings TEXT NOT NULL DEFAULT '[]',
                improved_output TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(goal_id) REFERENCES user_goals(id)
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_user_goals_created_at ON user_goals(created_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_goal_id ON agent_runs(goal_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_brain_routes_goal_id ON brain_routes(goal_id)")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_verification_results_goal_id ON verification_results(goal_id)"
        )

    def _ensure_columns(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(memory_records)").fetchall()
        }
        migrations = {
            "memory_type": "ALTER TABLE memory_records ADD COLUMN memory_type TEXT NOT NULL DEFAULT 'vector_memory'",
            "title": "ALTER TABLE memory_records ADD COLUMN title TEXT",
            "tags": "ALTER TABLE memory_records ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'",
            "source": "ALTER TABLE memory_records ADD COLUMN source TEXT",
            "updated_at": "ALTER TABLE memory_records ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
        }
        for column, statement in migrations.items():
            if column not in columns:
                connection.execute(statement)
        now = datetime.now(timezone.utc).isoformat()
        connection.execute("UPDATE memory_records SET updated_at = created_at WHERE updated_at = ''")
        connection.execute(
            "UPDATE memory_records SET memory_type = ? WHERE memory_type IS NULL OR memory_type = ''",
            (MemoryType.vector_memory.value,),
        )
        connection.execute("UPDATE memory_records SET tags = '[]' WHERE tags IS NULL OR tags = ''")
        connection.execute("UPDATE memory_records SET updated_at = ? WHERE updated_at IS NULL", (now,))

    def add(self, record: MemoryRecord) -> MemoryRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO memory_records
                (id, namespace, memory_type, kind, title, content, tags, metadata, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.namespace,
                    record.memory_type.value,
                    record.kind,
                    record.title,
                    record.content,
                    json.dumps(record.tags),
                    json.dumps(record.metadata),
                    record.source,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
        return record

    def search(
        self,
        query: str,
        namespace: str | None = "default",
        limit: int = 5,
        memory_type: MemoryType | None = None,
        tags: list[str] | None = None,
    ) -> list[MemoryRecord]:
        pattern = f"%{query}%"
        filters: list[str] = []
        params: list = []
        if namespace:
            filters.append("namespace = ?")
            params.append(namespace)
        if memory_type:
            filters.append("memory_type = ?")
            params.append(memory_type.value)
        if query:
            filters.append("(content LIKE ? OR kind LIKE ? OR title LIKE ?)")
            params.extend([pattern, pattern, pattern])
        for tag in tags or []:
            filters.append("tags LIKE ?")
            params.append(f"%{tag}%")
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM memory_records
                {where_clause}
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def list(
        self,
        namespace: str | None = "default",
        limit: int = 50,
        memory_type: MemoryType | None = None,
    ) -> list[MemoryRecord]:
        filters: list[str] = []
        params: list = []
        if namespace:
            filters.append("namespace = ?")
            params.append(namespace)
        if memory_type:
            filters.append("memory_type = ?")
            params.append(memory_type.value)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM memory_records
                {where_clause}
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get(self, record_id: str) -> MemoryRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM memory_records WHERE id = ?",
                (record_id,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def update(self, record_id: str, request: UpdateMemoryRequest) -> MemoryRecord | None:
        existing = self.get(record_id)
        if not existing:
            return None
        update_data = request.model_dump(exclude_unset=True)
        for non_nullable in ("content", "memory_type", "namespace", "kind", "tags", "metadata"):
            if update_data.get(non_nullable) is None:
                update_data.pop(non_nullable, None)
        if "memory_type" in update_data and update_data["memory_type"] is not None:
            update_data["memory_type"] = update_data["memory_type"].value
        if "tags" in update_data and update_data["tags"] is not None:
            update_data["tags"] = json.dumps(update_data["tags"])
        if "metadata" in update_data and update_data["metadata"] is not None:
            update_data["metadata"] = json.dumps(update_data["metadata"])
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        assignments = ", ".join(f"{column} = ?" for column in update_data)
        params = [*update_data.values(), record_id]
        with self._connect() as connection:
            connection.execute(
                f"UPDATE memory_records SET {assignments} WHERE id = ?",
                params,
            )
        return self.get(record_id)

    def delete(self, record_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM memory_records WHERE id = ?", (record_id,))
        return cursor.rowcount > 0

    def counts_by_type(
        self,
        namespace: str | None = None,
        memory_type: MemoryType | None = None,
    ) -> dict[str, int]:
        filters: list[str] = []
        params: list = []
        if namespace:
            filters.append("namespace = ?")
            params.append(namespace)
        if memory_type:
            filters.append("memory_type = ?")
            params.append(memory_type.value)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT memory_type, COUNT(*) AS count
                FROM memory_records
                {where_clause}
                GROUP BY memory_type
                """,
                params,
            ).fetchall()
        return {row["memory_type"]: row["count"] for row in rows}

    def save_user_goal(
        self,
        goal: str,
        detected_intent: str,
        metadata: dict | None = None,
    ) -> str:
        record_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_goals (id, goal, detected_intent, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    goal,
                    detected_intent,
                    json.dumps(metadata or {}),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return record_id

    def save_agent_run(
        self,
        goal_id: str,
        agent_name: str,
        status: str,
        output: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        record_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_runs (id, goal_id, agent_name, status, output, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    goal_id,
                    agent_name,
                    status,
                    output,
                    json.dumps(metadata or {}),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return record_id

    def save_brain_route(
        self,
        goal_id: str,
        selected_brain: str,
        fallback_brain: str | None,
        reason: str | None,
        execution_strategy: str | None,
        metadata: dict | None = None,
    ) -> str:
        record_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO brain_routes
                (id, goal_id, selected_brain, fallback_brain, reason, execution_strategy, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    goal_id,
                    selected_brain,
                    fallback_brain,
                    reason,
                    execution_strategy,
                    json.dumps(metadata or {}),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return record_id

    def save_verification_result(
        self,
        goal_id: str,
        ok: bool,
        score: float,
        findings: list[str],
        improved_output: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        record_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO verification_results
                (id, goal_id, ok, score, findings, improved_output, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    goal_id,
                    int(ok),
                    score,
                    json.dumps(findings),
                    improved_output,
                    json.dumps(metadata or {}),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return record_id

    def phase1_table_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        with self._connect() as connection:
            for table in ("user_goals", "agent_runs", "brain_routes", "verification_results"):
                row = connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
                counts[table] = int(row["count"])
        return counts

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            namespace=row["namespace"],
            memory_type=row["memory_type"],
            kind=row["kind"],
            title=row["title"],
            content=row["content"],
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
            source=row["source"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
