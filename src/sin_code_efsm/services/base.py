"""Base interface that every mock service implements.

Docs: services/base.py.doc.md
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI


# Status strings written into the `status()` dict by `BaseService.status`.
# Subclasses may also set their own status fields.
_STATUS_UP = "up"
_STATUS_DOWN = "down"


class BaseService(ABC):
    """Common contract for every mock service.

    A service is a stateful component (HTTP routes, DB, queue, ...) that
    mounts itself onto the shared FastAPI gateway and participates in
    the ephemeral lifecycle: `on_start` -> serving -> `on_stop` -> `reset`.
    """

    #: Stable name used in `status` dict and route prefixes (override).
    name: str = "base"

    def __init__(self) -> None:
        self._port: int | None = None
        self._running: bool = False

    @property
    def port(self) -> int | None:
        """Network port this service is reachable on (set by the orchestrator)."""
        return self._port

    @property
    def running(self) -> bool:
        """True between `on_start()` and `on_stop()`."""
        return self._running

    def bind_port(self, port: int) -> None:
        """Called by the orchestrator once the gateway port is known.

        Subclasses should not call this themselves; the orchestrator
        invokes it during `start()`.
        """
        self._port = port

    def status(self) -> dict[str, Any]:
        """Status snapshot included in `EphemeralMockServer.status`."""
        return {
            "status": _STATUS_UP if self._running else _STATUS_DOWN,
            "port": self._port,
            "name": self.name,
        }

    @abstractmethod
    def register_routes(self, app: "FastAPI") -> None:
        """Attach HTTP routes for this service to the shared gateway app.

        Subclasses must implement this; the orchestrator calls it
        exactly once during `start()`.
        """

    def on_start(self) -> None:
        """Called after the HTTP server is listening. Override for warm-up.

        The default just flips `_running` to `True`. Subclasses that
        need to do real work (e.g. seed a database) should override
        and call `super().on_start()`.
        """
        self._running = True

    def on_stop(self) -> None:
        """Called before the HTTP server shuts down. Override for flush logic.

        The default just flips `_running` to `False`. Subclasses that
        hold external resources (e.g. an open file handle) should
        override and call `super().on_stop()`.
        """
        self._running = False

    @abstractmethod
    def reset(self) -> None:
        """Wipe all in-memory state — true ephemeral cleanup.

        Called by `EphemeralMockServer.reset()` between tests. After
        `reset()`, the service is in the same state as a fresh
        instance.
        """
