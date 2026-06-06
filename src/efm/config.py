"""YAML config parser for EFM mock services.

Docs: config.doc.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def load_config(path: str | Path) -> dict[str, Any]:
    """Parse an EFM YAML config file.

    Supports ``.yaml`` / ``.yml`` and ``.json`` for convenience.
    Raises *FileNotFoundError* or *RuntimeError* (if PyYAML is missing).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = path.read_text(encoding="utf-8")

    if path.suffix == ".json":
        return json.loads(raw)

    if yaml is None:
        raise RuntimeError(
            "PyYAML is required for .yaml configs. Install: pip install pyyaml"
        )
    return yaml.safe_load(raw)


def validate_config(cfg: dict[str, Any]) -> None:
    """Minimal validation — raises *ValueError* with a clear message."""
    if not isinstance(cfg, dict):
        raise ValueError("Config root must be a mapping")
    services = cfg.get("services")
    if not services:
        raise ValueError("Config must contain a 'services' list")
    if not isinstance(services, list):
        raise ValueError("'services' must be a list")
    for idx, svc in enumerate(services):
        if not isinstance(svc, dict):
            raise ValueError(f"Service #{idx} must be a mapping")
        name = svc.get("name")
        if not name:
            raise ValueError(f"Service #{idx} is missing 'name'")
        svc_type = svc.get("type")
        if svc_type not in ("http", "sqlite"):
            raise ValueError(
                f"Service '{name}' has unsupported type '{svc_type}' (expected: http, sqlite)"
            )
