"""Docker compose generation helpers (optional).

Docs: docker.py.doc.md
"""
from __future__ import annotations

from typing import Any


# Compose file defaults. Centralized so the dict- and string- forms
# stay in lockstep.
_DEFAULT_SERVICES = ("http", "database", "auth", "queue", "storage")
_DEFAULT_IMAGE = "python:3.11-slim"
_DEFAULT_PORT = 8888
_COMPOSE_VERSION = "3.8"
_SERVER_CMD = "python -m sin_code_efsm.server"
_ENV_SERVICES_KEY = "EFSM_SERVICES"
_ENV_PORT_KEY = "EFSM_PORT"


def generate_compose(services: list[str] | None = None, port: int = _DEFAULT_PORT) -> dict[str, Any]:
    """Generate a minimal docker-compose dict for the EFSM stack.

    The resulting dict can be dumped with `yaml.dump` if PyYAML is installed.

    Args:
        services: Service names to enable. Defaults to all five
            (http, database, auth, queue, storage).
        port: Port the gateway listens on inside the container.

    Returns:
        A dict matching the docker-compose v3.8 schema (one service,
            the `efsm` gateway).
    """
    svc_names = services or list(_DEFAULT_SERVICES)
    return {
        "version": _COMPOSE_VERSION,
        "services": {
            "efsm": {
                "image": _DEFAULT_IMAGE,
                "ports": [f"{port}:{port}"],
                "environment": {
                    _ENV_SERVICES_KEY: ",".join(svc_names),
                    _ENV_PORT_KEY: str(port),
                },
                "command": _SERVER_CMD,
            }
        },
    }


def compose_to_yaml(services: list[str] | None = None, port: int = _DEFAULT_PORT) -> str:
    """Return a docker-compose YAML string (no PyYAML required).

    The string is built by hand to avoid forcing PyYAML on callers
    who only need the YAML output (e.g. embedding it in a project
    scaffold).
    """
    svc_names = services or list(_DEFAULT_SERVICES)
    lines = [
        f"version: '{_COMPOSE_VERSION}'",
        "services:",
        "  efsm:",
        f"    image: {_DEFAULT_IMAGE}",
        f"    ports:",
        f"      - \"{port}:{port}\"",
        "    environment:",
        f"      {_ENV_SERVICES_KEY}: {','.join(svc_names)}",
        f"      {_ENV_PORT_KEY}: \"{port}\"",
        f"    command: {_SERVER_CMD}",
    ]
    return "\n".join(lines) + "\n"
