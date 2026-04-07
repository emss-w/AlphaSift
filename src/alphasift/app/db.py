from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class MetadataStore:
    """SQLite-backed metadata store for app-facing runs and artifacts."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    error_message TEXT,
                    summary_json TEXT
                );

                CREATE TABLE IF NOT EXISTS experiment_runs (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    result_count INTEGER NOT NULL,
                    best_result_json TEXT,
                    artifacts_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );

                CREATE TABLE IF NOT EXISTS paper_sessions (
                    id TEXT PRIMARY KEY,
                    job_id TEXT,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    starting_cash REAL NOT NULL,
                    ending_equity REAL,
                    status TEXT NOT NULL,
                    summary_json TEXT,
                    artifacts_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );

                CREATE TABLE IF NOT EXISTS strategies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    owner_type TEXT NOT NULL,
                    owner_id TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ai_runs (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    run_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    input_json TEXT NOT NULL,
                    output_json TEXT,
                    error_message TEXT,
                    prompt_profile_id TEXT,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );

                CREATE TABLE IF NOT EXISTS prompt_profiles (
                    id TEXT PRIMARY KEY,
                    template_name TEXT NOT NULL,
                    run_type TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    temperature REAL,
                    created_at TEXT NOT NULL,
                    notes TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
                CREATE INDEX IF NOT EXISTS idx_experiment_runs_job_id ON experiment_runs(job_id);
                CREATE INDEX IF NOT EXISTS idx_paper_sessions_job_id ON paper_sessions(job_id);
                CREATE INDEX IF NOT EXISTS idx_artifacts_owner ON artifacts(owner_type, owner_id);
                CREATE INDEX IF NOT EXISTS idx_ai_runs_job_id ON ai_runs(job_id);
                CREATE INDEX IF NOT EXISTS idx_ai_runs_run_type ON ai_runs(run_type);
                CREATE INDEX IF NOT EXISTS idx_prompt_profiles_run_type ON prompt_profiles(run_type);
                """
            )

    def insert(self, table: str, values: dict[str, Any]) -> None:
        columns = ", ".join(values.keys())
        placeholders = ", ".join(["?"] * len(values))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        with self._connect() as connection:
            connection.execute(sql, tuple(values.values()))

    def update(self, table: str, row_id: str, values: dict[str, Any]) -> None:
        assignments = ", ".join([f"{column} = ?" for column in values.keys()])
        sql = f"UPDATE {table} SET {assignments} WHERE id = ?"
        with self._connect() as connection:
            connection.execute(sql, (*values.values(), row_id))

    def fetch_one(self, table: str, row_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE id = ?",
                (row_id,),
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    def fetch_all(self, table: str, *, order_by: str = "created_at DESC") -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(f"SELECT * FROM {table} ORDER BY {order_by}").fetchall()
        return [dict(row) for row in rows]

    def fetch_where(
        self,
        table: str,
        *,
        where: str,
        params: tuple[Any, ...],
        order_by: str = "created_at DESC",
    ) -> list[dict[str, Any]]:
        query = f"SELECT * FROM {table} WHERE {where} ORDER BY {order_by}"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]
