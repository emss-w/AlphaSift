from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from alphasift.sandbox.models import SandboxRunRequest, SandboxRunResult


class SandboxExecutionError(RuntimeError):
    """Raised when sandbox execution fails at the orchestrator layer."""


@dataclass(frozen=True)
class DockerSandboxPolicy:
    """Container policy for isolated code execution."""

    docker_bin: str
    image: str
    runtime: str
    memory_limit: str
    cpu_limit: str
    pids_limit: int


class DockerSandboxRunner:
    """Runs one-off sandbox containers with strict local policy."""

    def __init__(self, policy: DockerSandboxPolicy) -> None:
        self.policy = policy

    def run(self, request: SandboxRunRequest) -> SandboxRunResult:
        workspace = request.workspace_dir.resolve()
        input_dir = (workspace / "input").resolve()
        out_dir = (workspace / "out").resolve()
        if not input_dir.exists():
            raise SandboxExecutionError(f"Sandbox input dir not found: {input_dir}")
        out_dir.mkdir(parents=True, exist_ok=True)
        code_path = request.code_path.resolve()
        if not code_path.exists():
            raise SandboxExecutionError(f"Sandbox code file not found: {code_path}")

        container_name = f"alphasift-ai-{uuid4().hex[:12]}"
        command = self._build_command(
            container_name=container_name,
            input_dir=input_dir,
            out_dir=out_dir,
            code_path=code_path,
        )

        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
            )
            duration = time.perf_counter() - started
            return SandboxRunResult(
                success=(completed.returncode == 0),
                exit_code=completed.returncode,
                timed_out=False,
                duration_seconds=duration,
                stdout=completed.stdout,
                stderr=completed.stderr,
                command=command,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.perf_counter() - started
            self._force_remove_container(container_name)
            return SandboxRunResult(
                success=False,
                exit_code=None,
                timed_out=True,
                duration_seconds=duration,
                stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                stderr=exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
                command=command,
            )
        except OSError as exc:
            raise SandboxExecutionError(f"Failed to execute sandbox runner: {exc}") from exc

    def _build_command(
        self,
        *,
        container_name: str,
        input_dir: Path,
        out_dir: Path,
        code_path: Path,
    ) -> list[str]:
        command = [
            self.policy.docker_bin,
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            self.policy.memory_limit,
            "--cpus",
            self.policy.cpu_limit,
            "--pids-limit",
            str(self.policy.pids_limit),
            "--mount",
            f"type=bind,source={input_dir},target=/input,readonly",
            "--mount",
            f"type=bind,source={out_dir},target=/out",
        ]
        runtime = self.policy.runtime.strip()
        if runtime:
            command.extend(["--runtime", runtime])
        command.extend(
            [
                self.policy.image,
                "python",
                f"/input/{code_path.name}",
            ]
        )
        return command

    def _force_remove_container(self, container_name: str) -> None:
        try:
            subprocess.run(
                [
                    self.policy.docker_bin,
                    "rm",
                    "-f",
                    container_name,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            return
