"""In-memory pub/sub message queue mock.

Docs: queue.doc.md
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .base import BaseService


class QueueService(BaseService):
    """Ephemeral in-memory pub/sub queue.

    Messages are stored per-topic in RAM. ``reset()`` wipes all topics.
    """

    name = "queue"
    prefix = "/queue"

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._topics: dict[str, list[dict[str, Any]]] = {}

    # ── Core API ───────────────────────────────────────────────────────

    def publish(self, topic: str, message: dict[str, Any]) -> int:
        """Publish a message to *topic*. Returns the new message count."""
        with self._lock:
            self._topics.setdefault(topic, []).append(message)
            return len(self._topics[topic])

    def consume(self, topic: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return up to *limit* messages from *topic*."""
        with self._lock:
            return list(self._topics.get(topic, [])[:limit])

    def topics(self) -> list[str]:
        with self._lock:
            return list(self._topics.keys())

    # ── BaseService lifecycle ──────────────────────────────────────────

    def register_routes(self, app: FastAPI) -> None:
        @app.post(f"{self.prefix}/publish/{{topic}}")
        async def _publish(topic: str, request: Request):
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            count = self.publish(topic, payload)
            return {"topic": topic, "message_count": count}

        @app.get(f"{self.prefix}/consume/{{topic}}")
        async def _consume(topic: str, limit: int = 10):
            messages = self.consume(topic, limit)
            return {"topic": topic, "messages": messages, "count": len(messages)}

        @app.get(f"{self.prefix}/topics")
        async def _topics():
            return {"topics": self.topics()}

    def reset(self) -> None:
        with self._lock:
            self._topics.clear()
