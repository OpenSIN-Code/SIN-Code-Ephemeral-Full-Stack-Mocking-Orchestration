"""FullStack composition — bundles the five default services.

Docs: stack.doc.md
"""
from __future__ import annotations

from typing import Any

from .services.auth import AuthService
from .services.database import DatabaseService
from .services.http import HTTPService
from .services.queue import QueueService
from .services.storage import StorageService


class FullStack:
    """Convenience container that creates the five default services.

    Used by ``EphemeralMockServer`` when *services* is ``None``.
    """

    def __init__(self) -> None:
        self.http = HTTPService()
        self.database = DatabaseService()
        self.auth = AuthService()
        self.queue = QueueService()
        self.storage = StorageService()

    def as_dict(self) -> dict[str, Any]:
        return {
            "http": self.http,
            "database": self.database,
            "auth": self.auth,
            "queue": self.queue,
            "storage": self.storage,
        }

    def reset_all(self) -> None:
        """Reset every service in the stack (database schema is dropped)."""
        self.http.reset()
        self.database.hard_reset()
        self.auth.reset()
        self.queue.reset()
        self.storage.reset()
