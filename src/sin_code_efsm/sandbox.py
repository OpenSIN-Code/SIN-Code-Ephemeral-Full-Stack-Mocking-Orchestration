"""Docker-Sandbox für isolierte Agent-Execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    container_id: str


class DockerSandbox:
    """Isolierter Container für Agent-Code."""

    def __init__(self, base_image: str = "python:3.11-slim"):
        self.base_image = base_image
        self._client = None

    def _client_init(self):
        if self._client is None:
            import docker
            self._client = docker.from_env()

    def run_command(self, command: str, workdir: str = "/workspace", timeout: int = 60) -> SandboxResult:
        self._client_init()
        container = self._client.containers.run(
            self.base_image,
            command=command,
            detach=True,
            mem_limit="512m",
            cpu_quota=50000,
            network_mode="none",  # isolation
        )
        try:
            result = container.wait(timeout=timeout)
            stdout = container.logs(stdout=True, stderr=False).decode()
            stderr = container.logs(stdout=False, stderr=True).decode()
            return SandboxResult(
                exit_code=result.get("StatusCode", -1),
                stdout=stdout, stderr=stderr, container_id=container.id,
            )
        finally:
            container.remove(force=True)

    def run_with_network(self, command: str, network_name: str = "bridge", timeout: int = 60) -> SandboxResult:
        self._client_init()
        container = self._client.containers.run(
            self.base_image,
            command=command,
            detach=True,
            network_mode=network_name,
        )
        try:
            result = container.wait(timeout=timeout)
            return SandboxResult(
                exit_code=result.get("StatusCode", -1),
                stdout=container.logs(stdout=True, stderr=False).decode(),
                stderr=container.logs(stdout=False, stderr=True).decode(),
                container_id=container.id,
            )
        finally:
            container.remove(force=True)
