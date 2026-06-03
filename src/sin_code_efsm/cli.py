"""CLI for the Ephemeral Mock Orchestrator.

Docs: cli.py.doc.md
"""
from __future__ import annotations

import json
import threading

import typer

from .orchestrator import EphemeralOrchestrator

app = typer.Typer(help="SIN-Code Ephemeral Mock Orchestrator CLI")


# Default test command. `pytest` is the conventional choice for the
# Python projects this CLI targets; override via `--test-cmd`.
_DEFAULT_TEST_CMD = "pytest"

# Standard test result field names. Kept in module scope so the JSON
# keys are easy to find/grep.
_RESULT_FIELDS = ("exit_code", "stdout", "stderr", "success", "backend")


@app.command()
def setup(
    name: str,
    apis: list[str] = typer.Option([], "--api", help="External API to mock"),
    requires_db: bool = typer.Option(False, "--db"),
    test_cmd: str = typer.Option(_DEFAULT_TEST_CMD, "--test-cmd"),
    serve_mock: bool = typer.Option(False, "--serve-mock", help="Run HTTP mock server"),
):
    """Spin up an ephemeral environment and run tests.

    Args:
        name: Human-readable environment name.
        apis: External APIs to mock (one `--api` per name).
        requires_db: Set `DATABASE_URL` to in-memory SQLite.
        test_cmd: Shell command to run in the sandbox.
        serve_mock: Start the mock server in a background thread.
    """
    orch = EphemeralOrchestrator()
    ctx = {
        "name": name,
        "external_apis": apis,
        "requires_db": requires_db,
        "test_command": test_cmd,
    }
    env = orch.configure_from_task(ctx)
    summary = {
        "mock_port": env.mock_port,
        "db_dsn": env.db_dsn,
        "env_vars": env.env_vars,
        "sandbox_backend": env.sandbox_backend,
    }
    typer.echo("[EFSM] Environment prepared:")
    typer.echo(json.dumps(summary, indent=2))

    if serve_mock and apis:
        # Daemon thread — the mock server dies with the CLI process.
        thread = threading.Thread(target=orch.mock_server.run, daemon=True)
        thread.start()
        typer.echo(f"[EFSM] Mock server started on port {env.mock_port}")

    typer.echo(f"[EFSM] Running: {test_cmd}")
    # `with_network` mirrors whether the test needs to reach the mocks.
    result = orch.run_tests(test_cmd, with_network=bool(apis))
    typer.echo(json.dumps(result, indent=2))


if __name__ == "__main__":
    app()
