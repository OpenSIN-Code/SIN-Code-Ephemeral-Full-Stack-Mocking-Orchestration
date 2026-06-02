"""HTTP endpoint mocking service.

Docs: http.doc.md
"""
from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..state import StateStore
from .base import BaseService


_VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def _normalize(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"


def _key(method: str, path: str) -> str:
    return f"{method.upper()}::{_normalize(path)}"


class HTTPService(BaseService):
    """Mocks arbitrary REST endpoints.

    Endpoints are registered with ``add_endpoint(method, path, response)`` and
    are served under the ``/http`` prefix on the shared gateway. Unregistered
    paths return 404 with a ``{'error': 'endpoint not registered'}`` body so
    callers can distinguish "I forgot to register this" from a real outage.
    """

    name = "http"
    prefix = "/http"

    def __init__(self) -> None:
        super().__init__()
        self._endpoints = StateStore()
        self._call_log: list[dict[str, Any]] = []
        self._log_lock = threading.Lock()

    # ── Registration API ───────────────────────────────────────────────

    def add_endpoint(
        self,
        method: str,
        path: str,
        response: dict | list | str | int | float | None,
        status_code: int = 200,
    ) -> None:
        """Register a mock endpoint.

        Example::

            http.add_endpoint("GET", "/users/1", {"id": 1, "name": "Ada"})
        """
        method = method.upper()
        if method not in _VALID_METHODS:
            raise ValueError(f"unsupported HTTP method: {method}")
        self._endpoints.set(
            _key(method, path),
            {"response": response, "status_code": status_code},
        )

    def get_endpoint(self, method: str, path: str) -> dict | None:
        """Return the registered config for an endpoint, or ``None``."""
        return self._endpoints.get(_key(method, path))

    def remove_endpoint(self, method: str, path: str) -> bool:
        return self._endpoints.delete(_key(method, path))

    def endpoints(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for k in self._endpoints.keys():
            method, path = k.split("::", 1)
            out.append((method, path))
        return out

    # ── Call log (for assertions in tests) ─────────────────────────────

    def calls(self) -> list[dict[str, Any]]:
        with self._log_lock:
            return list(self._call_log)

    def clear_calls(self) -> None:
        with self._log_lock:
            self._call_log.clear()

    def _record_call(self, method: str, path: str, body: Any) -> None:
        with self._log_lock:
            self._call_log.append({"method": method, "path": path, "body": body})

    # ── BaseService lifecycle ──────────────────────────────────────────

    def register_routes(self, app: FastAPI) -> None:
        @app.api_route(
            f"{self.prefix}/{{path:path}}",
            methods=list(_VALID_METHODS),
        )
        async def _handle(request: Request, path: str):
            body: Any = None
            if request.method in ("POST", "PUT", "PATCH"):
                try:
                    body = await request.json()
                except Exception:
                    body = None
            full_path = _normalize(path)
            self._record_call(request.method, full_path, body)
            cfg = self._endpoints.get(_key(request.method, full_path))
            if cfg is None:
                return JSONResponse(
                    {"error": "endpoint not registered", "path": full_path},
                    status_code=404,
                )
            return JSONResponse(cfg["response"], status_code=cfg["status_code"])

    def reset(self) -> None:
        self._endpoints.reset()
        self.clear_calls()
