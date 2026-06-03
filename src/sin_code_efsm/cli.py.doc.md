# cli.py

Typer CLI for the Ephemeral Mock Orchestrator.

## What it does

Single `setup` subcommand that:

1. Configures a `TestEnvironment` from a task description.
2. Optionally serves the mock server in a background thread.
3. Runs a user-supplied test command inside the sandbox.

## Dependencies

- `orchestrator.py` — `EphemeralOrchestrator`

## Usage

```bash
sin-efsm setup my-task --api stripe --api github --db --test-cmd "pytest -q"
```

## Known caveats

- The CLI is intentionally minimal — most workflows should use
  `EphemeralOrchestrator` from Python directly for finer control.
- The mock server thread is a `daemon=True` thread; it dies with
  the CLI process.
- `--test-cmd` is run via `shell=True` inside the sandbox; do not
  pass untrusted input.
