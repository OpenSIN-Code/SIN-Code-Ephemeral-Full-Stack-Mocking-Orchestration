import json
import threading
import typer

from .orchestrator import EphemeralOrchestrator

app = typer.Typer(help="SIN-Code Ephemeral Mock Orchestrator CLI")


@app.command()
def setup(
    name: str,
    apis: list[str] = typer.Option([], "--api"),
    requires_db: bool = typer.Option(False, "--db"),
    test_cmd: str = typer.Option("pytest", "--test-cmd"),
):
    """Spin up ephemeral environment and run tests."""
    orch = EphemeralOrchestrator()
    ctx = {
        "name": name,
        "external_apis": apis,
        "requires_db": requires_db,
        "test_command": test_cmd,
    }
    env = orch.configure_from_task(ctx)
    typer.echo(f"[EFSM] Environment prepared: {json.dumps({
        'mock_port': env.mock_port,
        'db_dsn': env.db_dsn,
        'env_vars': env.env_vars,
    }, indent=2)}")

    # Start mock server in background
    t = threading.Thread(target=orch.mock_server.run, daemon=True)
    t.start()

    # Run tests
    typer.echo(f"[EFSM] Running: {test_cmd}")
    result = orch.run_tests(test_cmd, with_network=bool(apis))
    typer.echo(json.dumps(result, indent=2))


if __name__ == "__main__":
    app()
