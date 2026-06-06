"""Typer CLI for EFM — ``efm up``, ``efm down``, ``efm status``.

Docs: cli.doc.md
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import typer

from efm.config import load_config, validate_config
from efm.http_mock import start_http_mock
from efm.db_mock import start_sqlite_mock, stop_sqlite_mock
from efm.process import list_running, stop_all, read_pid, is_running

app = typer.Typer(help="EFM — Ephemeral Full-Stack Mocking")


def _load_services(config_path: str) -> list[dict[str, Any]]:
    cfg = load_config(config_path)
    validate_config(cfg)
    return cfg.get("services", [])


@app.command()
def up(
    config: str = typer.Argument(..., help="Path to EFM YAML config"),
):
    """Start all mock services defined in *config*."""
    services = _load_services(config)
    started: list[dict[str, Any]] = []

    for svc in services:
        name = svc["name"]
        svc_type = svc.get("type")

        # Skip if already running
        if read_pid(name) is not None and is_running(read_pid(name)):  # type: ignore[arg-type]
            typer.echo(f"[{name}] Already running (PID {read_pid(name)})")
            continue

        if svc_type == "http":
            port = svc.get("port", 8080)
            routes = svc.get("routes", [])
            pid = start_http_mock(name, port, routes)
            url = f"http://127.0.0.1:{port}"
            typer.echo(f"[{name}] HTTP mock up on {url} (PID {pid})")
            started.append({"name": name, "type": "http", "url": url, "pid": pid})

        elif svc_type == "sqlite":
            schema = svc.get("schema", "")
            seed = svc.get("seed", [])
            db_path = start_sqlite_mock(name, schema, seed)
            typer.echo(f"[{name}] SQLite mock ready at {db_path}")
            started.append({"name": name, "type": "sqlite", "path": db_path})

    if not started:
        typer.echo("No new services started.")
        raise typer.Exit(code=0)

    typer.echo(f"\nStarted {len(started)} service(s).")


@app.command()
def down(
    config: str = typer.Argument(..., help="Path to EFM YAML config"),
):
    """Stop all mock services defined in *config*."""
    services = _load_services(config)
    stopped = stop_all(services)

    for svc in services:
        if svc.get("type") == "sqlite":
            stop_sqlite_mock(svc["name"])
            if svc["name"] not in stopped:
                stopped.append(svc["name"])

    if stopped:
        typer.echo(f"Stopped {len(stopped)} service(s): {', '.join(stopped)}")
    else:
        typer.echo("No running services found.")


@app.command()
def status():
    """List all running EFM services."""
    running = list_running()
    if not running:
        typer.echo("No EFM services are currently running.")
        raise typer.Exit(code=0)

    typer.echo(f"{'NAME':<15} {'TYPE':<8} {'PID':<8}")
    typer.echo("-" * 35)
    for svc in running:
        typer.echo(f"{svc['name']:<15} {svc['type']:<8} {svc.get('pid', '-'):<8}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
