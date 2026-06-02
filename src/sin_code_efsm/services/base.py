"""Base interface that every mock service implements.

Docs: base.doc.md
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI


class BaseService(ABC):
    """Common contract for every mock service.

    A service is a stateful component (HTTP routes, DB, queue, ...) that mounts
    itself onto the shared FastAPI gateway and participates in the ephemeral
    lifecycle: ``on_start`` -> serving -> ``on_stop`` -> ``reset``.
    """

    #: Stable name used in ``status`` dict and route prefixes (override).
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
        return self._running

    def bind_port(self, port: int) -> None:
        """Called by the orchestrator once the gateway port is known."""
        self._port = port

    def status(self) -> dict[str, Any]:
        """Status snapshot included in ``EphemeralMockServer.status``."""
        return {
            "status": "up" if self._running else "down",
            "port": self._port,
            "name": self.name,
        }

    @abstractmethod
    def register_routes(self, app: "FastAPI") -> None:
        """Attach HTTP routes for this service to the shared gateway app."""

    def on_start(self) -> None:
        """Called after the HTTP server is listening. Override for warm-up."""
        self._running = True

    def on_stop(self) -> None:
        """Called before the HTTP server shuts down. Override for flush logic."""
        self._running = False

    @abstractmethod
    def reset(self) -> None:
        """Wipe all in-memory state — true ephemeral cleanup."""
