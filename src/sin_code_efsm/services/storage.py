"""Mock S3-like object storage.

Docs: storage.doc.md
"""
from __future__ import annotations

import base64
import threading
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .base import BaseService


class StorageService(BaseService):
    """In-memory dict-based object store.

    Objects are stored per-bucket in RAM. ``reset()`` wipes all buckets.
    """

    name = "storage"
    prefix = "/storage"

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self._buckets: dict[str, dict[str, Any]] = {}

    # ── Core API ───────────────────────────────────────────────────────

    def put_object(self, bucket: str, key: str, data: bytes | str, content_type: str = "application/octet-stream") -> dict[str, Any]:
        """Store an object. Returns metadata."""
        with self._lock:
            self._buckets.setdefault(bucket, {})
            if isinstance(data, str):
                data = data.encode("utf-8")
            self._buckets[bucket][key] = {
                "data": data,
                "content_type": content_type,
                "size": len(data),
            }
        return {"bucket": bucket, "key": key, "size": len(data)}

    def get_object(self, bucket: str, key: str) -> dict[str, Any] | None:
        with self._lock:
            return self._buckets.get(bucket, {}).get(key)

    def list_objects(self, bucket: str) -> list[str]:
        with self._lock:
            return list(self._buckets.get(bucket, {}).keys())

    def list_buckets(self) -> list[str]:
        with self._lock:
            return list(self._buckets.keys())

    def delete_object(self, bucket: str, key: str) -> bool:
        with self._lock:
            if bucket in self._buckets and key in self._buckets[bucket]:
                del self._buckets[bucket][key]
                return True
            return False

    # ── BaseService lifecycle ──────────────────────────────────────────

    def register_routes(self, app: FastAPI) -> None:
        @app.put(f"{self.prefix}/{{bucket}}/{{key:path}}")
        async def _put(bucket: str, key: str, request: Request):
            body = await request.body()
            content_type = request.headers.get("content-type", "application/octet-stream")
            meta = self.put_object(bucket, key, body, content_type)
            return meta

        @app.get(f"{self.prefix}/{{bucket}}/{{key:path}}")
        async def _get(bucket: str, key: str):
            obj = self.get_object(bucket, key)
            if obj is None:
                return JSONResponse({"error": "not found"}, status_code=404)
            return Response(
                content=obj["data"],
                media_type=obj["content_type"],
            )

        @app.get(f"{self.prefix}/{{bucket}}")
        async def _list_bucket(bucket: str):
            return {"bucket": bucket, "objects": self.list_objects(bucket)}

        @app.get(f"{self.prefix}/")
        async def _list_buckets():
            return {"buckets": self.list_buckets()}

        @app.delete(f"{self.prefix}/{{bucket}}/{{key:path}}")
        async def _delete(bucket: str, key: str):
            ok = self.delete_object(bucket, key)
            return {"deleted": ok}

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
