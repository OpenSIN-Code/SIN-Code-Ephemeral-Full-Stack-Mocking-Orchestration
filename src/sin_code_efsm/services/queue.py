"""In-memory pub/sub message queue mock.

Docs: services/queue.py.doc.md
"""
from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI, Request

from .base import BaseService


# Default page size for `consume`; matches what the gateway returns
# for `?limit=` when the caller omits the query parameter.
_DEFAULT_LIMIT = 10


class QueueService(BaseService):
    """Ephemeral in-memory pub/sub queue.

    Messages are stored per-topic in RAM. `reset()` wipes all topics.
    """

    name = "queue"
    prefix = "/queue"

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._topics: dict[str, list[dict[str, Any]]] = {}

    # ── Core API ───────────────────────────────────────────────────────

    def publish(self, topic: str, message: dict[str, Any]) -> int:
        """Publish a message to `topic`. Returns the new message count.

        Args:
            topic: Topic name. Created on first publish.
            message: JSON-serializable message body.

        Returns:
            The total number of messages now in the topic.
        """
        with self._lock:
            self._topics.setdefault(topic, []).append(message)
            return len(self._topics[topic])

    def consume(self, topic: str, limit: int = _DEFAULT_LIMIT) -> list[dict[str, Any]]:
        """Return up to `limit` messages from `topic` (peek, no pop)."""
        with self._lock:
            return list(self._topics.get(topic, [])[:limit])

    def topics(self) -> list[str]:
        """Snapshot of all topic names currently in the queue."""
        with self._lock:
            return list(self._topics.keys())

    # ── BaseService lifecycle ──────────────────────────────────────────

    def register_routes(self, app: FastAPI) -> None:
        """Mount `/queue/{publish,consume,topics}` on the gateway."""
        @app.post(f"{self.prefix}/publish/{{topic}}")
        async def _publish(topic: str, request: Request):
            try:
                payload = await request.json()
            except Exception:
                # Malformed JSON becomes an empty dict so the queue
                # still accepts the message — useful for testing
                # consumer error handling.
                payload = {}
            count = self.publish(topic, payload)
            return {"topic": topic, "message_count": count}

        @app.get(f"{self.prefix}/consume/{{topic}}")
        async def _consume(topic: str, limit: int = _DEFAULT_LIMIT):
            messages = self.consume(topic, limit)
            return {"topic": topic, "messages": messages, "count": len(messages)}

        @app.get(f"{self.prefix}/topics")
        async def _topics():
            return {"topics": self.topics()}

    def reset(self) -> None:
        """Wipe every topic."""
        with self._lock:
            self._topics.clear()
