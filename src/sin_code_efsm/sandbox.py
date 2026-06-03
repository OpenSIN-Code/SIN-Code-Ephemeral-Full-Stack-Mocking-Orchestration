"""Sandbox for isolated agent execution.

Prefers Docker; falls back to a local subprocess when Docker is not
available (with reduced isolation, clearly marked on the result).

Docs: sandbox.py.doc.md
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass


# Default image, memory limit, and timeouts. Centralized so callers
# can see (and tune) them in one place.
_DEFAULT_BASE_IMAGE = "python:3.11-slim"
_DEFAULT_MEM_LIMIT = "512m"   # caps a runaway agent at 512 MB
_DEFAULT_TIMEOUT = 60         # seconds

# `timeout(1)` returns 124 on timeout. We reuse that exit code for
# the subprocess fallback so callers can branch on it the same way
# regardless of backend.
_TIMEOUT_EXIT_CODE = 124

# Backend identifiers written into `SandboxResult.backend` and into
# the orchestrator's `TestEnvironment.sandbox_backend`. Kept as
# constants so consumers can grep for them.
_BACKEND_DOCKER = "docker"
_BACKEND_SUBPROCESS = "subprocess"


@dataclass
class SandboxResult:
    """Outcome of one sandboxed command.

    Attributes:
        exit_code: Process exit code (or `124` for timeout).
        stdout: Captured stdout (decoded with `errors="replace"`).
        stderr: Captured stderr.
        container_id: Docker container id, or `None` for subprocess.
        backend: Which backend produced the result.
    """

    exit_code: int
    stdout: str
    stderr: str
    container_id: str | None = None
    backend: str = _BACKEND_DOCKER


def docker_available() -> bool:
    """Check whether a usable Docker daemon is reachable.

    Returns:
        True if the `docker` Python package is importable and a
        `client.ping()` succeeds. False otherwise (silent — no
        exception is raised).
    """
    try:
        import docker
    except ImportError:
        return False
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        # Broad catch: any docker SDK error (no daemon, permission
        # denied, missing socket) is reported as "not available".
        return False


class DockerSandbox:
    """Isolated container for agent code (with subprocess fallback)."""

    def __init__(self, base_image: str = _DEFAULT_BASE_IMAGE, allow_fallback: bool = True):
        """Initialize the sandbox.

        Args:
            base_image: Docker image to use for the container.
            allow_fallback: If True (default), fall back to a local
                subprocess when no Docker daemon is reachable. Set
                False to require Docker (raises if unavailable).
        """
        self.base_image = base_image
        self.allow_fallback = allow_fallback
        # Lazy-init the docker client so constructing the sandbox
        # doesn't pay the import cost when the caller only needs
        # the subprocess fallback.
        self._client = None

    def _client_init(self):
        if self._client is None:
            import docker

            self._client = docker.from_env()
        return self._client

    def _run_subprocess(self, command: str, timeout: int) -> SandboxResult:
        """Run `command` in a local subprocess (no isolation).

        Used as the fallback when Docker is not available. Sets
        `backend="subprocess"` on the result so the caller can
        detect the degraded mode.
        """
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return SandboxResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                backend=_BACKEND_SUBPROCESS,
            )
        except subprocess.TimeoutExpired:
            # Exit code 124 matches GNU `timeout(1)` so callers
            # can branch on the same value regardless of backend.
            return SandboxResult(
                exit_code=_TIMEOUT_EXIT_CODE,
                stdout="",
                stderr=f"Timeout after {timeout}s",
                backend=_BACKEND_SUBPROCESS,
            )

    def run_command(
        self,
        command: str,
        timeout: int = _DEFAULT_TIMEOUT,
        network: bool = False,
        extra_hosts: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Run a shell command in the sandbox.

        Args:
            command: Shell command to execute. Wrapped in `sh -c`
                inside the container.
            timeout: Seconds to wait before killing the process.
            network: If True, attach the container to the `bridge`
                network. Default `False` for lockdown; tests that
                need to reach the host's mock server must set True.
            extra_hosts: Optional `host:ip` map to add to the
                container's `/etc/hosts`. The orchestrator uses
                this to wire `host.docker.internal -> host-gateway`.

        Returns:
            `SandboxResult` with `backend` set to `docker` or
            `subprocess` depending on which path ran.

        Raises:
            RuntimeError: If Docker is not available *and*
                `allow_fallback` is False.
        """
        if not docker_available():
            if not self.allow_fallback:
                raise RuntimeError("Docker not available and fallback disabled")
            return self._run_subprocess(command, timeout)

        client = self._client_init()
        kwargs: dict = {
            # `sh -c` so the user can pass `pytest -q && echo done`
            # style command strings, not just argv lists.
            "command": ["sh", "-c", command],
            # Detached so we can `wait()` and `logs()` separately.
            "detach": True,
            "mem_limit": _DEFAULT_MEM_LIMIT,
            # Network is opt-in (off by default) so a compromised
            # agent can't reach the internet for exfil.
            "network_mode": "bridge" if network else "none",
        }
        if extra_hosts:
            kwargs["extra_hosts"] = extra_hosts
        container = client.containers.run(self.base_image, **kwargs)
        try:
            result = container.wait(timeout=timeout)
            return SandboxResult(
                # `.get("StatusCode", -1)` is defensive against SDK
                # versions that return a different shape on error.
                exit_code=result.get("StatusCode", -1),
                # `errors="replace"` so a stray non-UTF8 byte doesn't
                # crash the decoder; the call site gets a sensible
                # string either way.
                stdout=container.logs(stdout=True, stderr=False).decode(errors="replace"),
                stderr=container.logs(stdout=False, stderr=True).decode(errors="replace"),
                container_id=container.id,
                backend=_BACKEND_DOCKER,
            )
        finally:
            # Always clean up the container, even on wait timeout
            # or SDK error. `force=True` removes a running container.
            try:
                container.remove(force=True)
            except Exception:
                # Best-effort cleanup; an orphaned container is
                # less bad than a leaked exception here.
                pass
