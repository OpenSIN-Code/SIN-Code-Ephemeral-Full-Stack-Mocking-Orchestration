"""FastAPI dynamic HTTP mock server from YAML config.

Generates routes at runtime and starts a uvicorn ASGI server on localhost.

Docs: http_mock.doc.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn


def build_app(routes: list[dict[str, Any]]) -> FastAPI:
    """Create a FastAPI app with dynamically-registered routes."""
    app = FastAPI(title="EFM HTTP Mock")

    for route in routes:
        path = route.get("path", "/")
        method = route.get("method", "GET").upper()
        response_body = route.get("response", "")
        status_code = route.get("status", 200)
        content_type = route.get("content_type", "")

        # Try to auto-detect JSON
        is_json = (
            content_type.startswith("application/json")
            or (not content_type and isinstance(response_body, str) and response_body.strip().startswith(("{", "[")))
        )

        def make_endpoint(body: Any = response_body, code: int = status_code, json_flag: bool = is_json):
            async def endpoint():
                if json_flag:
                    try:
                        data = json.loads(body) if isinstance(body, str) else body
                    except json.JSONDecodeError:
                        data = body
                    return JSONResponse(content=data, status_code=code)
                return PlainTextResponse(content=str(body), status_code=code)
            return endpoint

        endpoint_func = make_endpoint()

        # Register on the app
        if method == "GET":
            app.get(path)(endpoint_func)
        elif method == "POST":
            app.post(path)(endpoint_func)
        elif method == "PUT":
            app.put(path)(endpoint_func)
        elif method == "DELETE":
            app.delete(path)(endpoint_func)
        elif method == "PATCH":
            app.patch(path)(endpoint_func)
        else:
            app.add_api_route(path, endpoint_func, methods=[method])

    return app


def start_http_mock(name: str, port: int, routes: list[dict[str, Any]]) -> int:
    """Start a uvicorn server in a background process and return its PID."""
    from efm.process import spawn_python_module

    # Write a temporary JSON file with the route definitions so the child
    # process can read them without serialising closures across the fork.
    tmp = Path(f"/tmp/efm-{name}-routes.json")
    tmp.write_text(json.dumps({"routes": routes}), encoding="utf-8")

    return spawn_python_module(
        "efm.http_mock",
        [str(port), str(tmp)],
        name,
    )


def main() -> None:
    """Entry point used by the background process started via *start_http_mock*."""
    port = int(sys.argv[1])
    routes_file = Path(sys.argv[2])
    data = json.loads(routes_file.read_text(encoding="utf-8"))
    app = build_app(data["routes"])
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
