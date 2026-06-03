# __init__.py

Package entry point for `sin_code_efsm` (Ephemeral Full-Stack Mocking Orchestration).

## What it does

Re-exports the public API: `MockServer`, `StatefulMock`,
`DockerSandbox`, `SandboxResult`, `docker_available`,
`EphemeralOrchestrator`, `TestEnvironment`, and `EphemeralMockServer`.

## Public exports

| Symbol | Source |
|--------|--------|
| `MockServer`, `StatefulMock` | `mock_generator.py` |
| `DockerSandbox`, `SandboxResult`, `docker_available` | `sandbox.py` |
| `EphemeralOrchestrator`, `TestEnvironment` | `orchestrator.py` |
| `EphemeralMockServer` | `server.py` |

## Usage

```python
from sin_code_efsm import EphemeralMockServer
with EphemeralMockServer() as srv:
    print(srv.url, srv.status)
```

## Known caveats

- `DockerSandbox` requires the `docker` Python package; falls back to
  a local subprocess if unavailable (with reduced isolation).
- `EphemeralMockServer` requires `fastapi` + `uvicorn`.
