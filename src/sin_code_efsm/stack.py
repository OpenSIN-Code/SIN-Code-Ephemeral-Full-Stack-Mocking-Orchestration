"""FullStack composition — bundles the five default services.

Docs: stack.py.doc.md
"""
from __future__ import annotations

from typing import Any

from .services.auth import AuthService
from .services.database import DatabaseService
from .services.http import HTTPService
from .services.queue import QueueService
from .services.storage import StorageService


# The five default services, declared once for use as default values
# and as the canonical iteration order in `as_dict` / `reset_all`.
_DEFAULT_SERVICE_NAMES = ("http", "database", "auth", "queue", "storage")


class FullStack:
    """Convenience container that creates the five default services.

    Used by `EphemeralMockServer` when `services` is `None`.
    """

    def __init__(self) -> None:
        self.http = HTTPService()
        self.database = DatabaseService()
        self.auth = AuthService()
        self.queue = QueueService()
        self.storage = StorageService()

    def as_dict(self) -> dict[str, Any]:
        """Return the same services as a `{name: service}` dict.

        Iteration order matches `_DEFAULT_SERVICE_NAMES` so callers
        that rely on order (e.g. test snapshots) get a stable shape.
        """
        return {
            "http": self.http,
            "database": self.database,
            "auth": self.auth,
            "queue": self.queue,
            "storage": self.storage,
        }

    def reset_all(self) -> None:
        """Reset every service in the stack (database schema is dropped).

        Note: `database.hard_reset()` is used (not `reset()`), which
        drops the schema along with the rows. If you need to keep
        the schema, call `reset()` on the individual service.
        """
        # The database needs `hard_reset` to drop its schema; the
        # other services just need the standard `reset`.
        self.http.reset()
        self.database.hard_reset()
        self.auth.reset()
        self.queue.reset()
        self.storage.reset()
