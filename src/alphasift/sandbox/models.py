from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SandboxRunRequest:
    """Sandbox execution input for one isolated run."""

    workspace_dir: Path
    code_path: Path
    timeout_seconds: int


@dataclass(frozen=True)
class SandboxRunResult:
    """Sandbox execution result metadata."""

    success: bool
    exit_code: int | None
    timed_out: bool
    duration_seconds: float
    stdout: str
    stderr: str
    command: list[str]
