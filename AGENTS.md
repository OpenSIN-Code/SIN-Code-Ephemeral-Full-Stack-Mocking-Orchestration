# SIN-Code-Ephemeral-Full-Stack-Mocking-Orchestration — Agent-Engineering Hints

## What it does (1 sentence)
Ephemeral Full-Stack Mocking — spins up disposable mock environments (FastAPI HTTP servers + SQLite databases) from a single YAML config so tests and local development can run against a realistic but throwaway stack.

## Stack
- Language: Python
- Version: 0.1.0
- Test count: 51 tests
- CLI: `efm` with 3 subcommands (`up`, `down`, `status`)

## When to use
- Integration / E2E tests that need a real HTTP API + database without booting Docker or staging infra.
- Local development against a contract-defined backend before the real service exists.
- Reproducing a bug that requires a specific seed-data state without polluting a shared dev DB.

## Boundaries
- Do NOT touch the `*.bak` files (`pyproject.toml.bak`, `README.md.bak`) — they are pre-migration snapshots.
- Do NOT change the YAML schema (`services[].type`, `port`, `routes`, `schema`, `seed`) without a major-version bump — example configs in the wild depend on it.
- Always tear down with `efm down <config.yaml>` — orphaned processes will hold ports.
- Always keep `process.py` as the single owner of subprocess lifecycle — never spawn from `http_mock.py` / `db_mock.py` directly.
- Note: `src/sin_code_efsm/` is the legacy EFSM package kept alongside the new `src/efm/`; the supported CLI entry point is `efm`.

## Key files
- `src/efm/config.py` — YAML loader + schema validation.
- `src/efm/http_mock.py` — FastAPI dynamic-route builder (HTTP service type).
- `src/efm/db_mock.py` — SQLite schema + seed-data executor (sqlite service type).
- `src/efm/process.py` — subprocess lifecycle (start, stop, status, PID tracking).
- `src/efm/cli.py` — Typer CLI (`up`, `down`, `status`).
- `tests/test_efm.py`, `tests/test_efsm.py` — 51 tests covering config parsing, HTTP routes, DB seeding, and orchestrator state.

## Verification
- `pytest tests/ -q` — all 51 tests pass (~4s; 3 harmless `PytestCollectionWarning`s on `TestEnvironment` dataclass).
- `efm --help` — prints help with `up`, `down`, `status`.
- `efm status` — smoke test; should list running services (empty if none).
