# EFM — Ephemeral Full-Stack Mocking

Quickly spin up mock environments (HTTP APIs, SQLite databases) for testing
and local development.

## SOTA Status

- Tests: **51 passing** (`pytest tests/ -q`, ~4s; 3 harmless `PytestCollectionWarning`s on a `TestEnvironment` dataclass)
- CI: ![ci](https://img.shields.io/badge/ci-pending-lightgrey) (placeholder — wire up GitHub Actions)
- Maturity tier: **1 / 3** (MVP — v0.1.0, large test surface)
- Last commit: 2026-06-06

## Installation

```bash
cd ~/dev/SIN-Code-Ephemeral-Full-Stack-Mocking-Orchestration
pip install -e . --break-system-packages --no-deps
```

## Quick Start

Create a `mock_config.yaml`:

```yaml
services:
  - name: user-api
    type: http
    port: 8080
    routes:
      - path: /users
        method: GET
        response: '{"users": [{"id": 1, "name": "Alice"}]}'
  - name: test-db
    type: sqlite
    schema: |
      CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
    seed:
      - INSERT INTO users (id, name) VALUES (1, 'Alice');
```

Start everything:

```bash
efm up mock_config.yaml
```

Check status:

```bash
efm status
```

Tear down:

```bash
efm down mock_config.yaml
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `efm up <config.yaml>` | Start all services defined in the config |
| `efm down <config.yaml>` | Stop all services defined in the config |
| `efm status` | List running EFM services |

## Supported Service Types

- **http** — FastAPI server with dynamic routes, JSON/text responses, configurable status codes.
- **sqlite** — File-based SQLite database created from schema + seed data.

## Integration

This tool is exposed in the unified `sin code` hub:

```bash
sin code efm up   mock_config.yaml    # alias of: efm up mock_config.yaml
sin code efm down mock_config.yaml    # alias of: efm down mock_config.yaml
sin code efm status                   # alias of: efm status
```

See `AGENTS.md` for boundaries, key files, and verification steps.

## License

MIT
