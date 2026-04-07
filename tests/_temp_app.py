from __future__ import annotations

import shutil
import time
import uuid
from pathlib import Path


BASE_DIR = Path("tests/.tmp_app")


def make_workspace_temp_dir() -> Path:
    """Create a unique temp directory under tests/.tmp_app."""
    temp_dir = BASE_DIR / uuid.uuid4().hex
    temp_dir.mkdir(parents=True, exist_ok=False)
    return temp_dir


def cleanup_workspace_temp_dir(temp_dir: Path) -> None:
    """Remove test temp directory and prune base dir when empty."""
    _rmtree_with_retries(temp_dir)
    if BASE_DIR.exists() and not any(BASE_DIR.iterdir()):
        BASE_DIR.rmdir()


def cleanup_all_workspace_temp_dirs() -> None:
    """Remove the full app test temp root directory."""
    _rmtree_with_retries(BASE_DIR)


def _rmtree_with_retries(path: Path) -> None:
    for _ in range(20):
        shutil.rmtree(path, ignore_errors=True)
        if not path.exists():
            return
        time.sleep(0.05)
