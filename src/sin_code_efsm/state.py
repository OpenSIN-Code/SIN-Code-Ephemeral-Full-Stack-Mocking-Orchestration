"""Ephemeral state management for mock services.

Tracks service status, ports, and lifecycle transitions.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServiceRecord:
    """Tracks the status of a single mock service."""

    name: str
    status: str = "down"  # 'up' | 'down' | 'starting' | 'stopping'
    port: int | None = None
    host: str = "127.0.0.1"
    error: str | None = None
    service: Any = None  # The actual service instance


class StateManager:
    """Thread-safe state container for all mock services."""

    def __init__(self) -> None:
        self._records: dict[str, ServiceRecord] = {}
        self._lock = threading.Lock()

    def register(self, name: str, port: int | None = None) -> ServiceRecord:
        with self._lock:
            if name not in self._records:
                self._records[name] = ServiceRecord(name=name, port=port)
        return self._records[name]

    def set_service(self, name: str, service: Any) -> None:
        with self._lock:
            self._records[name].service = service

    def set_status(self, name: str, status: str) -> None:
        with self._lock:
            self._records[name].status = status

    def set_error(self, name: str, error: str) -> None:
        with self._lock:
            self._records[name].status = "error"
            self._records[name].error = error

    def clear(self, name: str) -> None:
        with self._lock:
            if name in self._records:
                self._records[name] = ServiceRecord(name=name)

    def get(self, name: str) -> ServiceRecord | None:
        return self._records.get(name)

    def all(self) -> dict[str, ServiceRecord]:
        with self._lock:
            return dict(self._records)

    def all_up(self) -> list[str]:
        with self._lock:
            return [n for n, r in self._records.items() if r.status == "up"]

    def drop(self) -> None:
        with self._lock:
            self._records.clear()


class StateStore:
    """Simple thread-safe key-value store with reset capability."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def get(self, key: str) -> Any | None:
        with self._lock:
            return self._data.get(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())

    def reset(self) -> None:
        with self._lock:
            self._data.clear()
