"""Docker compose generation helpers (optional).

Docs: docker.doc.md
"""
from __future__ import annotations

from typing import Any


def generate_compose(services: list[str] | None = None, port: int = 8888) -> dict[str, Any]:
    """Generate a minimal docker-compose dict for the EFSM stack.

    The resulting dict can be dumped with ``yaml.dump`` if PyYAML is installed.
    """
    svc_names = services or ["http", "database", "auth", "queue", "storage"]
    return {
        "version": "3.8",
        "services": {
            "efsm": {
                "image": "python:3.11-slim",
                "ports": [f"{port}:{port}"],
                "environment": {
                    "EFSM_SERVICES": ",".join(svc_names),
                    "EFSM_PORT": str(port),
                },
                "command": "python -m sin_code_efsm.server",
            }
        },
    }


def compose_to_yaml(services: list[str] | None = None, port: int = 8888) -> str:
    """Return a docker-compose YAML string (no PyYAML required)."""
    svc_names = services or ["http", "database", "auth", "queue", "storage"]
    lines = [
        "version: '3.8'",
        "services:",
        "  efsm:",
        "    image: python:3.11-slim",
        f"    ports:",
        f"      - \"{port}:{port}\"",
        "    environment:",
        f"      EFSM_SERVICES: {','.join(svc_names)}",
        f"      EFSM_PORT: \"{port}\"",
        "    command: python -m sin_code_efsm.server",
    ]
    return "\n".join(lines) + "\n"
