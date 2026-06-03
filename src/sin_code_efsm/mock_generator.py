"""Stateful mock server for external APIs.

Docs: mock_generator.py.doc.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# HTTP methods that the default `respond` knows how to handle.
# Anything else returns `{"status": "ok"}` with no side effect.
_WRITE_METHODS = ("PUT", "PATCH")


@dataclass
class StatefulMock:
    """A mock with real in-memory state.

    Attributes:
        name: Human-readable name.
        base_path: URL prefix (e.g. `/users`); `dispatch` routes
            requests whose path starts with this prefix to this mock.
        state: Per-resource in-memory data. Keyed by the *last* path
            segment (or `"root"` for `/`).
        scenarios: Optional canned responses keyed by `METHOD:/path`.
            Matched before the default CRUD dispatch.
    """

    name: str
    base_path: str
    state: dict[str, Any] = field(default_factory=dict)
    scenarios: dict[str, dict] = field(default_factory=dict)

    def respond(self, method: str, path: str, body: dict | None = None) -> dict:
        """Dispatch a request to the right branch.

        Args:
            method: HTTP method (uppercase or lowercase — callers are
                free to pass either).
            path: Full path including the mock's `base_path`.
            body: Request body for `POST` / `PUT` / `PATCH`.

        Returns:
            A JSON-friendly response dict. Canned `scenarios` win
            over the default CRUD behavior.
        """
        method = method.upper()
        key = f"{method}:{path}"
        if key in self.scenarios:
            return self.scenarios[key]
        # Resource = last non-empty path segment; fall back to "root"
        # so the empty-path case is still indexable in `state`.
        resource = path.strip("/").split("/")[-1] or "root"
        if method == "POST":
            self.state.setdefault(resource, []).append(body)
            return {
                "status": "created",
                "id": len(self.state[resource]),
                "data": body,
            }
        if method == "GET":
            return {"data": self.state.get(resource, [])}
        if method == "DELETE":
            self.state.pop(resource, None)
            return {"status": "deleted", "resource": resource}
        if method in _WRITE_METHODS:
            self.state[resource] = body
            return {"status": "updated", "data": body}
        return {"status": "ok"}


class MockServer:
    """Mock server holding multiple `StatefulMock`s.

    The FastAPI layer is optional: if FastAPI is not installed, the
    server can still be exercised in-process via `dispatch()`.
    """

    def __init__(self) -> None:
        self.mocks: dict[str, StatefulMock] = {}
        # Lazy-built so the FastAPI import isn't paid by callers
        # that only need `dispatch()` for tests.
        self._app = None

    def add_mock(self, mock: StatefulMock) -> None:
        """Register a mock under `mock.base_path`."""
        self.mocks[mock.base_path] = mock

    def dispatch(self, method: str, path: str, body: dict | None = None) -> dict:
        """Route a request without going through the HTTP layer.

        Args:
            method: HTTP method.
            path: Full request path (leading slash optional).
            body: Request body for write methods.

        Returns:
            The matched mock's response, or `{"error": "no mock matched", ...}`
            if no mock's `base_path` is a prefix of `path`.
        """
        # Normalize: every path is treated as starting with `/` so
        # the prefix match works regardless of caller style.
        normalized = path if path.startswith("/") else f"/{path}"
        for base, mock in self.mocks.items():
            prefix = base if base.startswith("/") else f"/{base}"
            if normalized.startswith(prefix):
                return mock.respond(method, normalized, body)
        return {"error": "no mock matched", "path": normalized}

    @property
    def app(self):
        """Lazy-built FastAPI app for the mock server."""
        if self._app is None:
            self._app = self._build_app()
        return self._app

    def _build_app(self):
        """Construct the FastAPI app with a catch-all route."""
        try:
            from fastapi import FastAPI, Request
            from fastapi.responses import JSONResponse
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "FastAPI is required to run the HTTP mock server. "
                "Install with: pip install fastapi uvicorn"
            ) from exc

        app = FastAPI(title="SIN-Code Ephemeral Mock Server")

        @app.api_route(
            "/{path:path}",
            methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )
        async def catch_all(request: Request, path: str):  # noqa: ANN001
            body = None
            if request.method in ("POST", "PUT", "PATCH"):
                try:
                    body = await request.json()
                except Exception:
                    # Body-parse failures become None rather than 400
                    # so the mock stays useful for partial / malformed
                    # requests the user might want to test.
                    body = None
            result = self.dispatch(request.method, f"/{path}", body)
            # Surface "no mock matched" as 404 so clients can branch
            # on it; everything else is 200 (the mock decides its
            # own shape, not its status semantics).
            status = 404 if result.get("error") == "no mock matched" else 200
            return JSONResponse(result, status_code=status)

        return app

    def run(self, host: str = "127.0.0.1", port: int = 8787) -> None:  # pragma: no cover
        """Serve the mock over HTTP via uvicorn. Blocks."""
        import uvicorn

        uvicorn.run(self.app, host=host, port=port)
