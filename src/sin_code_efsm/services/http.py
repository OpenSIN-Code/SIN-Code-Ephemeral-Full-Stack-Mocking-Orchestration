"""HTTP endpoint mocking service.

Docs: services/http.py.doc.md
"""
from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..state import StateStore
from .base import BaseService


# Closed set of HTTP methods this mock knows how to serve.
# Anything else is rejected by `add_endpoint` with a clear error.
_VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

# Methods that *carry a body* and therefore need JSON parsing in the
# request handler. Used by `register_routes._handle` to decide whether
# to call `await request.json()`.
_WRITE_METHODS = ("POST", "PUT", "PATCH")

# Delimiter between method and path in the `StateStore` key. Chosen
# to be illegal in HTTP paths so a user-supplied path can't collide
# with the separator.
_KEY_SEP = "::"


def _normalize(path: str) -> str:
    """Ensure `path` starts with `/`."""
    return path if path.startswith("/") else f"/{path}"


def _key(method: str, path: str) -> str:
    """Build the StateStore key for an (method, path) pair."""
    return f"{method.upper()}{_KEY_SEP}{_normalize(path)}"


class HTTPService(BaseService):
    """Mocks arbitrary REST endpoints.

    Endpoints are registered with `add_endpoint(method, path, response)`
    and are served under the `/http` prefix on the shared gateway.
    Unregistered paths return 404 with
    `{"error": "endpoint not registered", "path": "..."}` so callers
    can distinguish "I forgot to register this" from a real outage.
    """

    name = "http"
    prefix = "/http"

    def __init__(self) -> None:
        super().__init__()
        self._endpoints = StateStore()
        self._call_log: list[dict[str, Any]] = []
        # Lock separate from the StateStore's so `calls()` doesn't
        # contend with endpoint registration.
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

        Args:
            method: HTTP method (case-insensitive).
            path: URL path (leading slash optional).
            response: Response body. Anything `JSONResponse` can serialize.
            status_code: HTTP status code to return (default 200).

        Raises:
            ValueError: If `method` is not in `_VALID_METHODS`.

        Example:
            http.add_endpoint("GET", "/users/1", {"id": 1, "name": "Ada"})
        """
        method = method.upper()
        if method not in _VALID_METHODS:
            raise ValueError(f"unsupported HTTP method: {method}")
        # `setdefault` semantics — re-registering the same key
        # overwrites silently. This is intentional: tests often
        # need to swap a fixture between cases.
        self._endpoints.set(
            _key(method, path),
            {"response": response, "status_code": status_code},
        )

    def get_endpoint(self, method: str, path: str) -> dict | None:
        """Return the registered config for an endpoint, or `None`."""
        return self._endpoints.get(_key(method, path))

    def remove_endpoint(self, method: str, path: str) -> bool:
        """Remove a registration. Returns `True` if it existed."""
        return self._endpoints.delete(_key(method, path))

    def endpoints(self) -> list[tuple[str, str]]:
        """List all `(method, path)` tuples currently registered."""
        out: list[tuple[str, str]] = []
        for k in self._endpoints.keys():
            method, path = k.split(_KEY_SEP, 1)
            out.append((method, path))
        return out

    # ── Call log (for assertions in tests) ─────────────────────────────

    def calls(self) -> list[dict[str, Any]]:
        """Snapshot of recorded requests (defensive copy)."""
        with self._log_lock:
            return list(self._call_log)

    def clear_calls(self) -> None:
        """Empty the call log."""
        with self._log_lock:
            self._call_log.clear()

    def _record_call(self, method: str, path: str, body: Any) -> None:
        """Append one entry to the call log (under the lock)."""
        with self._log_lock:
            self._call_log.append({"method": method, "path": path, "body": body})

    # ── BaseService lifecycle ──────────────────────────────────────────

    def register_routes(self, app: FastAPI) -> None:
        """Mount a catch-all route for `/http/{path:path}`."""
        @app.api_route(
            f"{self.prefix}/{{path:path}}",
            methods=list(_VALID_METHODS),
        )
        async def _handle(request: Request, path: str):
            body: Any = None
            if request.method in _WRITE_METHODS:
                try:
                    body = await request.json()
                except Exception:
                    # Body-parse failures become None so the mock
                    # stays useful for partial / malformed requests.
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
        """Drop all endpoints and clear the call log."""
        self._endpoints.reset()
        self.clear_calls()
