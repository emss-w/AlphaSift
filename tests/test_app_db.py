from __future__ import annotations
from alphasift.app.db import MetadataStore
from alphasift.app.jobs import create_job, mark_job_completed, mark_job_running, utc_now_iso
from tests._temp_app import cleanup_workspace_temp_dir, make_workspace_temp_dir


def test_database_initialization_creates_tables():
    temp_dir = make_workspace_temp_dir()
    try:
        db_path = temp_dir / "app" / "metadata.sqlite3"
        store = MetadataStore(db_path)

        assert db_path.exists()
        assert store.fetch_all("jobs") == []
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_insert_and_retrieve_job():
    temp_dir = make_workspace_temp_dir()
    try:
        store = MetadataStore(temp_dir / "metadata.sqlite3")

        job = create_job(store, kind="experiment_sma_cross")
        running = mark_job_running(store, job_id=job["id"])
        completed = mark_job_completed(store, job_id=job["id"], summary={"ok": True})

        assert running["status"] == "running"
        assert completed["status"] == "completed"
        assert store.fetch_one("jobs", job["id"]) is not None
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_insert_and_retrieve_experiment_metadata():
    temp_dir = make_workspace_temp_dir()
    try:
        store = MetadataStore(temp_dir / "metadata.sqlite3")
        job = create_job(store, kind="experiment_sma_cross")

        run_id = "exp_1"
        store.insert(
            "experiment_runs",
            {
                "id": run_id,
                "job_id": job["id"],
                "strategy_name": "SimpleMovingAverageCrossStrategy",
                "symbol": "BTC/USD",
                "timeframe": "60",
                "parameters_json": "{}",
                "result_count": 1,
                "best_result_json": "{}",
                "artifacts_json": "[]",
                "created_at": utc_now_iso(),
            },
        )

        run = store.fetch_one("experiment_runs", run_id)
        assert run is not None
        assert run["job_id"] == job["id"]
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_insert_and_retrieve_paper_session_metadata():
    temp_dir = make_workspace_temp_dir()
    try:
        store = MetadataStore(temp_dir / "metadata.sqlite3")
        job = create_job(store, kind="paper_session")

        session_id = "paper_1"
        store.insert(
            "paper_sessions",
            {
                "id": session_id,
                "job_id": job["id"],
                "strategy_name": "Buy and Hold",
                "symbol": "BTC/USD",
                "timeframe": "60",
                "starting_cash": 10000.0,
                "ending_equity": 10250.0,
                "status": "completed",
                "summary_json": "{}",
                "artifacts_json": "[]",
                "created_at": utc_now_iso(),
            },
        )

        session = store.fetch_one("paper_sessions", session_id)
        assert session is not None
        assert session["status"] == "completed"
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_artifact_metadata_persists():
    temp_dir = make_workspace_temp_dir()
    try:
        store = MetadataStore(temp_dir / "metadata.sqlite3")

        artifact_id = "artifact_1"
        store.insert(
            "artifacts",
            {
                "id": artifact_id,
                "kind": "experiment_results_csv",
                "path": str(temp_dir / "results.csv"),
                "created_at": utc_now_iso(),
                "owner_type": "experiment_run",
                "owner_id": "exp_1",
            },
        )

        artifact = store.fetch_one("artifacts", artifact_id)
        assert artifact is not None
        assert artifact["owner_id"] == "exp_1"
    finally:
        cleanup_workspace_temp_dir(temp_dir)
