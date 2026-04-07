from __future__ import annotations

import atexit

from tests._temp_app import cleanup_all_workspace_temp_dirs


atexit.register(cleanup_all_workspace_temp_dirs)


def pytest_sessionstart(session) -> None:
    cleanup_all_workspace_temp_dirs()


def pytest_sessionfinish(session, exitstatus: int) -> None:
    cleanup_all_workspace_temp_dirs()
