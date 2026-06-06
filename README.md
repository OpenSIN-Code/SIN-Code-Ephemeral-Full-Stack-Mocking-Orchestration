# EFM — Ephemeral Full-Stack Mocking

Quickly spin up mock environments (HTTP APIs, SQLite databases) for testing
and local development.

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

## License

MIT
