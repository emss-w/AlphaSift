from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from alphasift.app.db import MetadataStore

PENDING = "pending"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"

ALLOWED_STATUSES = {PENDING, RUNNING, COMPLETED, FAILED}


def utc_now_iso() -> str:
    """Return current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def create_job(store: MetadataStore, *, kind: str) -> dict[str, Any]:
    """Create a pending job record."""
    job = {
        "id": uuid4().hex,
        "kind": kind,
        "status": PENDING,
        "created_at": utc_now_iso(),
        "started_at": None,
        "finished_at": None,
        "error_message": None,
        "summary_json": None,
    }
    store.insert("jobs", job)
    return job


def mark_job_running(store: MetadataStore, *, job_id: str) -> dict[str, Any]:
    """Mark a job as running."""
    updates = {"status": RUNNING, "started_at": utc_now_iso(), "error_message": None}
    store.update("jobs", job_id, updates)
    job = store.fetch_one("jobs", job_id)
    if job is None:
        raise ValueError(f"Job not found: {job_id}")
    return job


def mark_job_completed(
    store: MetadataStore,
    *,
    job_id: str,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Mark a job as completed with an optional summary payload."""
    summary_json = json.dumps(summary, sort_keys=True) if summary is not None else None
    updates = {
        "status": COMPLETED,
        "finished_at": utc_now_iso(),
        "summary_json": summary_json,
        "error_message": None,
    }
    store.update("jobs", job_id, updates)
    job = store.fetch_one("jobs", job_id)
    if job is None:
        raise ValueError(f"Job not found: {job_id}")
    return job


def mark_job_failed(store: MetadataStore, *, job_id: str, error_message: str) -> dict[str, Any]:
    """Mark a job as failed with a stable error message."""
    updates = {
        "status": FAILED,
        "finished_at": utc_now_iso(),
        "error_message": error_message,
    }
    store.update("jobs", job_id, updates)
    job = store.fetch_one("jobs", job_id)
    if job is None:
        raise ValueError(f"Job not found: {job_id}")
    return job
