"""EphemeralMockServer — main orchestration class for the mock stack.

Docs: server.py.doc.md
"""
from __future__ import annotations

import signal
import socket
import threading
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .orchestrator import EphemeralOrchestrator
from .services.auth import AuthService
from .services.base import BaseService
from .services.database import DatabaseService
from .services.http import HTTPService
from .services.queue import QueueService
from .services.storage import StorageService
from .state import StateManager
from .stack import FullStack


# ── EphemeralMockServer ──────────────────────────────────────────────


class EphemeralMockServer:
    """Spin up a complete ephemeral mock stack on a single HTTP gateway.

    Parameters
    ----------
    port:
        Preferred port. If occupied, the next free port is picked automatically.
    services:
        List of service names to enable. ``None`` means all five defaults.
    """

    _ALL_SERVICES = ("http", "database", "auth", "queue", "storage")

    def __init__(self, port: int = 8888, services: list[str] | None = None) -> None:
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
        """Start all configured mock services in ephemeral mode."""
        if self._server is not None:
            raise RuntimeError("Server is already running")

        self._sock = self._create_bound_socket()
        self._actual_port = self._sock.getsockname()[1]
        self._build_app()
        assert self._app is not None

        cfg = uvicorn.Config(
            self._app,
            host="127.0.0.1",
            port=self._actual_port,
            log_level="warning",
        )
        self._server = uvicorn.Server(cfg)
        self._thread = threading.Thread(target=self._server.run, kwargs={"sockets": [self._sock]}, daemon=True)
        self._thread.start()

        # Wait until the server is actually listening
        for _ in range(200):
            if self._server.started:
                break
            import time

            time.sleep(0.01)
        else:
            raise RuntimeError("Server failed to start within 2 seconds")

        # Signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, self._signal_handler)
            except ValueError:
                pass  # signal only works in main thread

        # Warm-up services
        for svc in self._service_map.values():
            svc.bind_port(self._actual_port)
            svc.on_start()
            self._state.set_status(svc.name, "up")

    def stop(self) -> None:
        """Tear down all services."""
        if self._server is None:
            return

        for svc in self._service_map.values():
            svc.on_stop()
            self._state.set_status(svc.name, "down")

        self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5)
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
        self._server = None
        self._thread = None
        self._sock = None
        self._actual_port = None
        self._app = None
        self._service_map.clear()
        self._state.drop()

    def _signal_handler(self, signum: int, frame: Any) -> None:
        self.stop()

    def _create_bound_socket(self) -> socket.socket:
        """Create a socket bound to the preferred port, or any free port."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", self._preferred_port))
        except OSError:
            sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        return sock

    # ── Endpoint helpers (delegate to HTTPService) ─────────────────────

    def add_endpoint(self, method: str, path: str, response: dict | list | str | int | float | None) -> None:
        """Register a mock REST endpoint on the HTTP service."""
        http: HTTPService | None = self._service_map.get("http")  # type: ignore[assignment]
        if http is None:
            raise RuntimeError("HTTP service is not enabled")
        http.add_endpoint(method, path, response)

    def get_endpoint(self, method: str, path: str) -> dict | None:
        """Return the registered config for an endpoint, or ``None``."""
        http: HTTPService | None = self._service_map.get("http")  # type: ignore[assignment]
        if http is None:
            raise RuntimeError("HTTP service is not enabled")
        return http.get_endpoint(method, path)

    def reset(self) -> None:
        """Reset all services to their initial state."""
        for svc in self._service_map.values():
            svc.reset()

    # ── Status ───────────────────────────────────────────────────────────

    @property
    def status(self) -> dict[str, dict[str, Any]]:
        """Return a dict of ``{service_name: {status: 'up', port: 9001, ...}}``."""
        return {
            name: {
                **svc.status(),
                "port": self._actual_port,
            }
            for name, svc in self._service_map.items()
        }

    @property
    def port(self) -> int | None:
        """The actual port the server is listening on."""
        return self._actual_port

    @property
    def url(self) -> str:
        """Base URL of the running gateway."""
        if self._actual_port is None:
            raise RuntimeError("Server is not running")
        return f"http://127.0.0.1:{self._actual_port}"

    # ── Internal helpers ───────────────────────────────────────────────

    def _build_app(self) -> None:
        self._app = FastAPI(title="SIN-Code EFSM Gateway")
        svc_names = self._services_cfg or list(self._ALL_SERVICES)

        for name in svc_names:
            svc = self._create_service(name)
            self._service_map[name] = svc
            self._state.register(name, port=self._actual_port)
            svc.register_routes(self._app)

        # Catch-all health endpoint
        @self._app.get("/health")
        async def _health() -> dict[str, Any]:
            return {"status": "ok", "services": list(self._service_map.keys())}

    def _create_service(self, name: str) -> BaseService:
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
