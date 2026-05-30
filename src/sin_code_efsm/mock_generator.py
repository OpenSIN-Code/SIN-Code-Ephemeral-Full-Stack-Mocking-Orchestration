"""Stateful Mock-Server für externe APIs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


@dataclass
class StatefulMock:
    """Mock mit echtem Zustand."""
    name: str
    base_path: str
    state: dict[str, Any] = field(default_factory=dict)
    scenarios: dict[str, dict] = field(default_factory=dict)

    def respond(self, method: str, path: str, body: dict | None = None) -> dict:
        key = f"{method}:{path}"
        if key in self.scenarios:
            return self.scenarios[key]
        # Default: echo with state update
        if method == "POST":
            resource = path.strip("/").split("/")[-1]
            self.state.setdefault(resource, []).append(body)
            return {"status": "created", "id": len(self.state[resource]), "data": body}
        elif method == "GET":
            resource = path.strip("/").split("/")[-1]
            return {"data": self.state.get(resource, [])}
        return {"status": "ok"}


class MockServer:
    """FastAPI-basierter Mock-Server mit mehreren Stateful-Mocks."""

    def __init__(self):
        self.app = FastAPI(title="SIN-Code Ephemeral Mock Server")
        self.mocks: dict[str, StatefulMock] = {}
        self._register_routes()

    def add_mock(self, mock: StatefulMock):
        self.mocks[mock.base_path] = mock

    def _register_routes(self):
        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def catch_all(request: Request, path: str):
            # Route to matching mock by prefix
            for base, mock in self.mocks.items():
                if path.startswith(base.lstrip("/")):
                    body = None
                    if request.method in ("POST", "PUT", "PATCH"):
                        try:
                            body = await request.json()
                        except Exception:
                            body = None
                    result = mock.respond(request.method, f"/{path}", body)
                    return JSONResponse(result)
            return JSONResponse({"error": "no mock matched", "path": path}, status_code=404)

    def run(self, host: str = "127.0.0.1", port: int = 8787):
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)
