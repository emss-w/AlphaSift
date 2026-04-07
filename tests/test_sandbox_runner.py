from __future__ import annotations

import subprocess
from pathlib import Path

from alphasift.sandbox.models import SandboxRunRequest
from alphasift.sandbox.runner import DockerSandboxPolicy, DockerSandboxRunner
from tests._temp_app import cleanup_workspace_temp_dir, make_workspace_temp_dir


def _make_workspace(temp_dir: Path) -> tuple[Path, Path]:
    workspace = temp_dir / "sandbox_run"
    input_dir = workspace / "input"
    out_dir = workspace / "out"
    input_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    code_path = input_dir / "task.py"
    code_path.write_text("print('ok')\n", encoding="utf-8")
    return workspace, code_path


def test_docker_runner_builds_network_isolated_command(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        workspace, code_path = _make_workspace(temp_dir)
        captured: dict[str, list[str]] = {}

        def _stub_run(command, **kwargs):
            captured["command"] = list(command)
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        monkeypatch.setattr("alphasift.sandbox.runner.subprocess.run", _stub_run)

        runner = DockerSandboxRunner(
            DockerSandboxPolicy(
                docker_bin="docker",
                image="python:3.11-slim",
                runtime="runsc",
                memory_limit="512m",
                cpu_limit="1.0",
                pids_limit=128,
            )
        )
        result = runner.run(
            SandboxRunRequest(
                workspace_dir=workspace,
                code_path=code_path,
                timeout_seconds=30,
            )
        )

        assert result.success is True
        command = captured["command"]
        assert "docker" == command[0]
        assert "--network" in command and command[command.index("--network") + 1] == "none"
        assert "--runtime" in command and command[command.index("--runtime") + 1] == "runsc"
        assert "--rm" in command
    finally:
        cleanup_workspace_temp_dir(temp_dir)


def test_docker_runner_handles_timeout(monkeypatch):
    temp_dir = make_workspace_temp_dir()
    try:
        workspace, code_path = _make_workspace(temp_dir)
        calls: list[list[str]] = []

        def _stub_run(command, **kwargs):
            calls.append(list(command))
            if command[1:3] == ["run", "--rm"]:
                raise subprocess.TimeoutExpired(command, timeout=1, output="", stderr="")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        monkeypatch.setattr("alphasift.sandbox.runner.subprocess.run", _stub_run)

        runner = DockerSandboxRunner(
            DockerSandboxPolicy(
                docker_bin="docker",
                image="python:3.11-slim",
                runtime="runsc",
                memory_limit="512m",
                cpu_limit="1.0",
                pids_limit=128,
            )
        )
        result = runner.run(
            SandboxRunRequest(
                workspace_dir=workspace,
                code_path=code_path,
                timeout_seconds=1,
            )
        )

        assert result.success is False
        assert result.timed_out is True
        assert any(call[1:3] == ["rm", "-f"] for call in calls)
    finally:
        cleanup_workspace_temp_dir(temp_dir)
