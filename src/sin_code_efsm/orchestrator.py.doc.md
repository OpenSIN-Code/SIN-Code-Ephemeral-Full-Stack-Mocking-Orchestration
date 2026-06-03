# orchestrator.py

Top-level orchestrator that wires the mock server and sandbox together.

## What it does

`EphemeralOrchestrator` accepts a `task_context` dict (matching what
an agent would supply) and returns a fully-prepared `TestEnvironment`:

- Each external API gets a `StatefulMock` + an `*_BASE_URL` env var.
- Database requests get a `DATABASE_URL` (in-memory SQLite).
- The sandbox backend is auto-detected: Docker if available,
  subprocess otherwise.

`run_tests` then runs the user's test command in the sandbox and
returns a dict with exit code, stdout/stderr, and which backend was
used.

## Dependencies

- `mock_generator.py` — `MockServer`, `StatefulMock`
- `sandbox.py` — `DockerSandbox`, `docker_available`

## Public API

| Symbol | Purpose |
|--------|---------|
| `TestEnvironment` | Dataclass: mock_port, db_dsn, container_id, env_vars, sandbox_backend |
| `EphemeralOrchestrator` | The orchestrator class |
| `EphemeralOrchestrator.configure_from_task(ctx)` | Build a `TestEnvironment` from a task dict |
| `EphemeralOrchestrator.run_tests(cmd, with_network)` | Run a test command and return the result |

## Task-context keys

| Key | Required | Description |
|-----|----------|-------------|
| `name` | yes | Human-readable environment name |
| `external_apis` | no | List of API names to mock |
| `requires_db` | no | If true, set `DATABASE_URL` to in-memory SQLite |
| `test_command` | yes | Shell command to run in the sandbox |

## Known caveats

- `host` switches between `host.docker.internal` (Docker) and
  `127.0.0.1` (subprocess fallback). The env var uses the Docker
  host when the sandbox is Docker, so the in-container test can
  reach the host's mock server.
- `stdout` / `stderr` are truncated to 2000 chars to keep the
  return payload small.
- The orchestrator does NOT verify that the test command is
  safe; pass trusted input.
