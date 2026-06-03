"""EphemeralMockServer — main orchestration class for the mock stack.

Docs: server.py.doc.md
"""
from __future__ import annotations

import signal
import socket
import threading
import time
from typing import Any

import uvicorn
from fastapi import FastAPI

from .orchestrator import EphemeralOrchestrator
from .services.auth import AuthService
from .services.base import BaseService
from .services.database import DatabaseService
from .services.http import HTTPService
from .services.queue import QueueService
from .services.storage import StorageService
from .state import StateManager
from .stack import FullStack


# Default port for the shared gateway. 8888 is the convention for
# local-dev "alt HTTP" services; pick something else with the
# `port` argument.
_DEFAULT_PORT = 8888

# Wait for uvicorn to mark itself started. 200 * 10ms = 2 seconds.
# This bound is deliberately tight — a healthy uvicorn is up in <100ms
# on a local socket; if it takes >2s the test environment is broken.
_STARTUP_POLL_COUNT = 200
_STARTUP_POLL_INTERVAL_S = 0.01
_STARTUP_TIMEOUT_S = _STARTUP_POLL_COUNT * _STARTUP_POLL_INTERVAL_S  # 2s

# Listen backlog for the bound socket. 128 matches the Linux default
# `somaxconn` for non-superuser processes.
_LISTEN_BACKLOG = 128

# Maximum time to wait for the uvicorn thread to exit on `stop()`.
# Anything longer means `stop()` returns with a still-running thread.
_JOIN_TIMEOUT_S = 5

# Bind address for the gateway. Localhost only — these mocks are not
# meant to be exposed to other hosts.
_BIND_HOST = "127.0.0.1"

# Quiet uvicorn logs by default. The mock server is noisy enough
# already; access logs would dominate test output.
_UVICORN_LOG_LEVEL = "warning"

# Status string the StateManager records for a healthy service.
_STATUS_UP = "up"
_STATUS_DOWN = "down"


class EphemeralMockServer:
    """Spin up a complete ephemeral mock stack on a single HTTP gateway.

    Args:
        port: Preferred port. If occupied, the next free port is
            picked automatically.
        services: List of service names to enable. `None` means all
            five defaults (`http`, `database`, `auth`, `queue`,
            `storage`).
    """

    _ALL_SERVICES = ("http", "database", "auth", "queue", "storage")

    def __init__(self, port: int = _DEFAULT_PORT, services: list[str] | None = None) -> None:
        self._preferred_port = port
        self._actual_port: int | None = None
        self._services_cfg = services
        self._state = StateManager()
        self._app: FastAPI | None = None
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self._sock: socket.socket | None = None
        self._service_map: dict[str, BaseService] = {}
        self._orchestrator = EphemeralOrchestrator(mock_port=port)
        self._stack = FullStack()

    # ── Lifecycle ──────────────────────────────────────────────────────

    def start(self) -> None:
        """Start all configured mock services in ephemeral mode.

        Raises:
            RuntimeError: If the server is already running, or if
                uvicorn fails to mark itself started within
                `_STARTUP_TIMEOUT_S` seconds.
        """
        if self._server is not None:
            raise RuntimeError("Server is already running")

        self._sock = self._create_bound_socket()
        # `getsockname()[1]` returns the actual bound port — either
        # the preferred one or whatever the kernel picked.
        self._actual_port = self._sock.getsockname()[1]
        self._build_app()
        assert self._app is not None

        cfg = uvicorn.Config(
            self._app,
            host=_BIND_HOST,
            port=self._actual_port,
            log_level=_UVICORN_LOG_LEVEL,
        )
        self._server = uvicorn.Server(cfg)
        # Pass the pre-bound socket to uvicorn so it accepts on the
        # exact port we picked (no race with another process grabbing
        # it between `_create_bound_socket` and `uvicorn.run`).
        self._thread = threading.Thread(
            target=self._server.run,
            kwargs={"sockets": [self._sock]},
            daemon=True,
        )
        self._thread.start()

        # Poll for uvicorn's `started` flag. The 10ms interval keeps
        # `start()` responsive (no large blocking sleep) without
        # burning CPU.
        for _ in range(_STARTUP_POLL_COUNT):
            if self._server.started:
                break
            time.sleep(_STARTUP_POLL_INTERVAL_S)
        else:
            raise RuntimeError(
                f"Server failed to start within {_STARTUP_TIMEOUT_S:.1f} seconds"
            )

        # Wire up graceful-shutdown signal handlers. `signal.signal`
        # raises `ValueError` if called from a non-main thread;
        # we swallow that so `start()` works in worker threads too.
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, self._signal_handler)
            except ValueError:
                pass  # signal only works in main thread

        # Warm-up: tell every service its port and let it run its
        # start hook. Order matters — `bind_port` must come before
        # `on_start` in case the hook reads the port.
        for svc in self._service_map.values():
            svc.bind_port(self._actual_port)
            svc.on_start()
            self._state.set_status(svc.name, _STATUS_UP)

    def stop(self) -> None:
        """Tear down all services.

        Idempotent: a second call after the server is already
        stopped is a no-op.
        """
        if self._server is None:
            return

        for svc in self._service_map.values():
            svc.on_stop()
            self._state.set_status(svc.name, _STATUS_DOWN)

        # Ask uvicorn to exit, then wait briefly for the thread.
        # We do NOT `join()` forever — a stuck server should not
        # block the caller indefinitely.
        self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=_JOIN_TIMEOUT_S)
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
        # Reset state so a subsequent `start()` builds a fresh server.
        self._server = None
        self._thread = None
        self._sock = None
        self._actual_port = None
        self._app = None
        self._service_map.clear()
        self._state.drop()

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """SIGINT/SIGTERM handler — delegates to `stop()`."""
        self.stop()

    def _create_bound_socket(self) -> socket.socket:
        """Create a socket bound to the preferred port, or any free port.

        If the preferred port is taken, we fall back to `port=0` so
        the kernel picks a free one. `SO_REUSEADDR` is set so quick
        `start`/`stop` cycles on the same port don't hit TIME_WAIT.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((_BIND_HOST, self._preferred_port))
        except OSError:
            # Preferred port is taken; ask the kernel for any free port.
            sock.bind((_BIND_HOST, 0))
        sock.listen(_LISTEN_BACKLOG)
        return sock

    # ── Endpoint helpers (delegate to HTTPService) ─────────────────────

    def add_endpoint(
        self, method: str, path: str, response: dict | list | str | int | float | None
    ) -> None:
        """Register a mock REST endpoint on the HTTP service.

        Raises:
            RuntimeError: If the HTTP service was not enabled in
                `services=` (e.g. user passed `services=("database",)`).
        """
        http: HTTPService | None = self._service_map.get("http")  # type: ignore[assignment]
        if http is None:
            raise RuntimeError("HTTP service is not enabled")
        http.add_endpoint(method, path, response)

    def get_endpoint(self, method: str, path: str) -> dict | None:
        """Return the registered config for an endpoint, or `None`.

        Raises:
            RuntimeError: If the HTTP service was not enabled.
        """
        http: HTTPService | None = self._service_map.get("http")  # type: ignore[assignment]
        if http is None:
            raise RuntimeError("HTTP service is not enabled")
        return http.get_endpoint(method, path)

    def reset(self) -> None:
        """Reset all services to their initial state (data, not schema)."""
        for svc in self._service_map.values():
            svc.reset()

    # ── Status ───────────────────────────────────────────────────────────

    @property
    def status(self) -> dict[str, dict[str, Any]]:
        """Per-service status snapshot.

        Returns a dict mapping `service_name` to its `status()` dict
        plus the shared `port`.
        """
        return {
            name: {
                **svc.status(),
                "port": self._actual_port,
            }
            for name, svc in self._service_map.items()
        }

    @property
    def port(self) -> int | None:
        """The actual port the server is listening on (`None` when stopped)."""
        return self._actual_port

    @property
    def url(self) -> str:
        """Base URL of the running gateway.

        Raises:
            RuntimeError: If the server is not running.
        """
        if self._actual_port is None:
            raise RuntimeError("Server is not running")
        return f"http://{_BIND_HOST}:{self._actual_port}"

    # ── Internal helpers ───────────────────────────────────────────────

    def _build_app(self) -> None:
        """Construct the FastAPI app and register each service's routes."""
        self._app = FastAPI(title="SIN-Code EFSM Gateway")
        svc_names = self._services_cfg or list(self._ALL_SERVICES)

        for name in svc_names:
            svc = self._create_service(name)
            self._service_map[name] = svc
            self._state.register(name, port=self._actual_port)
            svc.register_routes(self._app)

        # Catch-all health endpoint. Useful for `curl` smoke tests
        # and for the agent-toolbox to verify the gateway is up.
        @self._app.get("/health")
        async def _health() -> dict[str, Any]:
            return {"status": "ok", "services": list(self._service_map.keys())}

    def _create_service(self, name: str) -> BaseService:
        """Factory: build a service instance by name.

        Raises:
            ValueError: If `name` is not one of the recognized services.
        """
        if name == "http":
            return HTTPService()
        if name == "database":
            return DatabaseService()
        if name == "auth":
            return AuthService()
        if name == "queue":
            return QueueService()
        if name == "storage":
            return StorageService()
        raise ValueError(f"Unknown service: {name}")
