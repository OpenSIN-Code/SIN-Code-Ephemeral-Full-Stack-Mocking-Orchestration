# EFM Skill — Ephemeral Full-Stack Mocking

## When to use

Use this skill when the user needs to:
- Mock REST APIs for integration tests
- Create temporary SQLite databases with seed data
- Spin up ephemeral dependencies for local development

## CLI Commands

```bash
efm up <config.yaml>      # Start mocks
efm down <config.yaml>    # Stop mocks
efm status                # List running mocks
```

## Config Format (YAML)

```yaml
services:
  - name: my-api
    type: http
    port: 8080
    routes:
      - path: /health
        method: GET
        response: '{"status": "ok"}'
  - name: my-db
    type: sqlite
    schema: |
      CREATE TABLE t (id INTEGER PRIMARY KEY);
    seed:
      - INSERT INTO t (id) VALUES (1);
```

## Python API

```python
from efm.config import load_config, validate_config
from efm.http_mock import build_app, start_http_mock
from efm.db_mock import start_sqlite_mock, get_connection
from efm.process import list_running, stop_all
```

## Implementation Notes

- HTTP mocks run in background processes via uvicorn.
- SQLite mocks are file-based under `/tmp` so they persist until `efm down`.
- PID files live in `/tmp/efm-<name>.pid` for reliable lifecycle tracking.
