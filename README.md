# SIN-Code Ephemeral Full-Stack Mocking Orchestration (EFSM)

> Spin up a complete, isolated, ephemeral mock stack in under 2 seconds — HTTP, database, auth, queue, and storage — all in-memory, no Docker, no real services.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

Part of the [SIN-Code](https://github.com/OpenSIN-Code) agent-engineering stack. Install all subsystems together via the [SIN-Code Bundle](https://github.com/OpenSIN-Code/SIN-Code-Bundle).

## Features

- **EphemeralMockServer** — one class starts all five services on a single port
- **HTTP service** — mock arbitrary REST endpoints with per-method registration
- **Database service** — in-memory SQLite with schema setup/teardown
- **Auth service** — mock OAuth2 / JWT issuance and validation (HS256, no deps)
- **Queue service** — in-memory pub/sub per topic
- **Storage service** — dict-based S3-like object store
- **True ephemeral** — all data wiped on `stop()`, no external dependencies
- **Fast startup** — < 2 seconds, no Docker required
- **Random port allocation** — falls back automatically if preferred port is taken
- **Graceful shutdown** — SIGINT / SIGTERM handlers included
- **MCP server** — orchestrate mocks from AI agents via the Model Context Protocol

## Installation

```bash
pip install -e .
```

Optional MCP server support:
```bash
pip install -e ".[mcp]"
```

See [INSTALL.md](./INSTALL.md) for detailed setup instructions.

## Usage

### Library

```python
from sin_code_efsm import EphemeralMockServer

server = EphemeralMockServer(port=8888)
server.start()
print(server.url)  # http://127.0.0.1:8888

server.add_endpoint("GET", "/hello", {"msg": "world"})

import httpx
r = httpx.get(f"{server.url}/http/hello")
print(r.json())  # {"msg": "world"}

server.stop()  # everything vanishes
```

### Services

| Service | Prefix | What it does |
|---------|--------|--------------|
| HTTP | `/http` | Mock REST endpoints |
| Database | `/db` | In-memory SQLite + HTTP SQL execution |
| Auth | `/auth` | OAuth2 token + JWT userinfo |
| Queue | `/queue` | Pub/sub per topic |
| Storage | `/storage` | S3-like object store |

### CLI

```bash
# Spin up ephemeral environment and run tests
efsm setup my-test --api https://api.example.com --db --test-cmd pytest

# Serve mock server in background
efsm setup my-test --api https://api.example.com --serve-mock
```

## Testing

```bash
pytest tests/ -v
```

## MCP Server

Run the MCP server for agent integration:

```bash
python -m sin_code_efsm.mcp_server
```

Tools exposed:
- `generate_mock(service_spec, format="json")` — generate a mock service from an OpenAPI or GraphQL spec
- `orchestrate_mock(services, scenario="default")` — orchestrate ephemeral mock services for integration testing

## Integration

EFSM is designed to work as part of the SIN-Code ecosystem:

- **SIN-Code Bundle** — orchestrates all subsystems from a single CLI (`sin`)
- **Orchestration** — spin up mock stacks as part of CI/agent workflows
- **Verification Oracle** — run integration tests against ephemeral mocks

## Documentation

- [INSTALL.md](./INSTALL.md)
- [docs/USAGE.md](./docs/USAGE.md)
- [docs/CONFIGURATION.md](./docs/CONFIGURATION.md)
- [CONTRIBUTING.md](./CONTRIBUTING.md)
- [CHANGELOG.md](./CHANGELOG.md)
- CoDocs: `src/sin_code_efsm/server.py.doc.md`, `src/sin_code_efsm/services/http.py.doc.md`

## Note on isolation

Docker gives the strongest isolation. When Docker is not present, EFSM falls back to a resource-limited subprocess runner — convenient for local/CI use, but not a security boundary for untrusted code.

## License

MIT — see [LICENSE](./LICENSE).
