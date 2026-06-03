"""Orchestrate the mock server and sandbox for an agent task.

Docs: orchestrator.py.doc.md
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .mock_generator import MockServer, StatefulMock
from .sandbox import DockerSandbox, docker_available


# Default mock-server port. 8787 is unprivileged and rarely conflicts
# with common dev tools.
_DEFAULT_MOCK_PORT = 8787

# Truncation limit for test stdout/stderr captured in the result
# dict. 2000 chars is enough for a "did it pass?" glance without
# bloating the response payload.
_OUTPUT_TRUNCATE_CHARS = 2000

# Sentinel exit code for the orchestrator itself failing (as opposed
# to the test command failing). -1 is the conventional "not run" code.
_ORCHESTRATOR_ERROR_EXIT = -1

# Standard test-result field names, centralized so the JSON shape
# is grep-friendly.
_RESULT_KEYS = ("exit_code", "stdout", "stderr", "success", "backend")


@dataclass
class TestEnvironment:
    """Prepared test environment for a single agent task.

    Attributes:
        mock_port: Port the mock gateway is reachable on.
        db_dsn: SQLAlchemy-compatible DSN (in-memory SQLite) or None.
        container_id: Running container id, or None (subprocess backend).
        env_vars: Extra env vars to inject (`*_BASE_URL`, `DATABASE_URL`).
        sandbox_backend: `docker` or `subprocess` (auto-detected).
    """

    mock_port: int
    db_dsn: str | None
    container_id: str | None
    env_vars: dict[str, str] = field(default_factory=dict)
    sandbox_backend: str = "docker"


class EphemeralOrchestrator:
    """Build a complete test environment for an agent task."""

    def __init__(self, mock_port: int = _DEFAULT_MOCK_PORT):
        """Initialize the orchestrator.

        Args:
            mock_port: Port the mock server binds to.
        """
        self.mock_server = MockServer()
        self.sandbox = DockerSandbox()
        self._mock_port = mock_port

    def configure_from_task(self, task_context: dict) -> TestEnvironment:
        """Build a `TestEnvironment` from a task description.

        Args:
            task_context: Dict with keys `name`, `external_apis`,
                `requires_db`, `test_command`.

        Returns:
            A fully-populated `TestEnvironment`. The mock server has
            one `StatefulMock` per external API; `env_vars` carries
            `*_BASE_URL` for each API plus `DATABASE_URL` if a DB
            was requested.
        """
        env_vars: dict[str, str] = {}
        # Pick the right host string for the sandbox backend.
        # `host.docker.internal` is the Docker Desktop convention
        # for "this container's host"; `127.0.0.1` is the correct
        # value when the test runs in the same process (subprocess
        # fallback).
        host = "host.docker.internal" if docker_available() else "127.0.0.1"
        for api in task_context.get("external_apis", []):
            self.mock_server.add_mock(StatefulMock(name=api, base_path=f"/{api}"))
            env_vars[f"{api.upper()}_BASE_URL"] = (
                f"http://{host}:{self._mock_port}/{api}"
            )

        db_dsn = None
        if task_context.get("requires_db"):
            # `:memory:` SQLite is the only DSN we surface today;
            # real-DB DSNs would need a connection-pool story.
            db_dsn = "sqlite:///:memory:"
            env_vars["DATABASE_URL"] = db_dsn

        return TestEnvironment(
            mock_port=self._mock_port,
            db_dsn=db_dsn,
            container_id=None,
            env_vars=env_vars,
            sandbox_backend="docker" if docker_available() else "subprocess",
        )

    def run_tests(self, test_command: str, with_network: bool = True) -> dict:
        """Run a test command inside the sandbox and return its result.

        Args:
            test_command: Shell command to run.
            with_network: If True, allow network access (needed when
                the test reaches the mock server via the host).
                Adds `host.docker.internal:host-gateway` to the
                container's `/etc/hosts`.

        Returns:
            Dict with `exit_code`, `stdout` (truncated), `stderr`
            (truncated), `success`, and `backend` (which sandbox was
            used). If the orchestrator itself fails, the dict
            reports `exit_code=-1` and `backend="none"`.
        """
        # `host-gateway` is the standard Docker Desktop value for
        # "the host's gateway IP". On Linux without Docker Desktop
        # this is a no-op, so the cost of always adding it is low.
        extra_hosts = (
            {"host.docker.internal": "host-gateway"} if with_network else None
        )
        try:
            result = self.sandbox.run_command(
                test_command,
                timeout=120,
                network=with_network,
                extra_hosts=extra_hosts,
            )
            return {
                "exit_code": result.exit_code,
                "stdout": result.stdout[:_OUTPUT_TRUNCATE_CHARS],
                "stderr": result.stderr[:_OUTPUT_TRUNCATE_CHARS],
                "success": result.exit_code == 0,
                "backend": result.backend,
            }
        except Exception as exc:
            # Catch-all so the orchestrator always returns a dict,
            # never raises. The error message goes into `stderr` so
            # callers can log / display it uniformly.
            return {
                "exit_code": _ORCHESTRATOR_ERROR_EXIT,
                "stdout": "",
                "stderr": str(exc),
                "success": False,
                "backend": "none",
            }
