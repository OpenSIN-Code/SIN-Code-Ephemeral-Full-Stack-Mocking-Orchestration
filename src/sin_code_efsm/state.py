"""Ephemeral state management for mock services.

Tracks service status, ports, and lifecycle transitions.

Docs: state.py.doc.md
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any


# Lifecycle status strings. Centralized as constants so consumers
# (e.g. dashboards) can `import` them and avoid typo'd string
# comparisons.
_STATUS_DOWN = "down"
_STATUS_UP = "up"
_STATUS_ERROR = "error"

# Default host for a registered service record. The orchestrator
# overwrites this when the service binds to a port.
_DEFAULT_HOST = "127.0.0.1"


@dataclass
class ServiceRecord:
    """Tracks the status of a single mock service.

    Attributes:
        name: Stable service identifier.
        status: One of `down` / `up` / `error` (see module constants).
        port: Port the service is bound to (`None` until bound).
        host: Bind host (default `127.0.0.1`).
        error: Error message if `status == "error"`.
        service: The live service instance (set by the orchestrator).
    """

    name: str
    status: str = _STATUS_DOWN
    port: int | None = None
    host: str = _DEFAULT_HOST
    error: str | None = None
    service: Any = None  # The actual service instance


class StateManager:
    """Thread-safe state container for all mock services."""

    def __init__(self) -> None:
        self._records: dict[str, ServiceRecord] = {}
        self._lock = threading.Lock()

    def register(self, name: str, port: int | None = None) -> ServiceRecord:
        """Create the record if missing and return it.

        Idempotent: re-registering an existing name is a no-op
        (returns the existing record).
        """
        with self._lock:
            if name not in self._records:
                self._records[name] = ServiceRecord(name=name, port=port)
        return self._records[name]

    def set_service(self, name: str, service: Any) -> None:
        """Attach the live service instance to the record."""
        with self._lock:
            self._records[name].service = service

    def set_status(self, name: str, status: str) -> None:
        """Update the lifecycle status of a service."""
        with self._lock:
            self._records[name].status = status

    def set_error(self, name: str, error: str) -> None:
        """Mark a service as in error state and record the message."""
        with self._lock:
            self._records[name].status = _STATUS_ERROR
            self._records[name].error = error

    def clear(self, name: str) -> None:
        """Reset a single record to its default state."""
        with self._lock:
            if name in self._records:
                self._records[name] = ServiceRecord(name=name)

    def get(self, name: str) -> ServiceRecord | None:
        """Return the record for `name` (no lock — see caveat).

        Returns the live reference; do not mutate. For a snapshot,
        use `all()` instead.
        """
        return self._records.get(name)

    def all(self) -> dict[str, ServiceRecord]:
        """Snapshot of all records (defensive copy)."""
        with self._lock:
            return dict(self._records)

    def all_up(self) -> list[str]:
        """Names of all services currently in `up` state."""
        with self._lock:
            return [n for n, r in self._records.items() if r.status == _STATUS_UP]

    def drop(self) -> None:
        """Wipe every record."""
        with self._lock:
            self._records.clear()


class StateStore:
    """Simple thread-safe key-value store with reset capability."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any) -> None:
        """Store `value` under `key` (overwrites)."""
        with self._lock:
            self._data[key] = value

    def get(self, key: str) -> Any | None:
        """Return the value for `key`, or `None` if missing.

        The returned value is the live reference; do not mutate.
        """
        with self._lock:
            return self._data.get(key)

    def delete(self, key: str) -> bool:
        """Remove `key`. Returns `True` if it existed, `False` otherwise."""
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def keys(self) -> list[str]:
        """Snapshot of all keys (defensive copy)."""
        with self._lock:
            return list(self._data.keys())

    def reset(self) -> None:
        """Wipe every key."""
        with self._lock:
            self._data.clear()
