# services/base.py

Abstract base class for every mock service.

## What it does

Defines the contract that `EphemeralMockServer` relies on: each
service has a stable `name`, mounts itself onto the shared FastAPI
gateway via `register_routes(app)`, and participates in the
ephemeral lifecycle (`on_start` → `on_stop` → `reset`).

## Dependencies

- `abc.ABC` (stdlib) for the abstract base
- `fastapi` (TYPE_CHECKING only) for the route type hint

## Public API

| Symbol | Purpose |
|--------|---------|
| `BaseService` | Abstract base |
| `name` (class attr) | Stable identifier used in `status` and route prefixes |
| `port` / `running` | Read-only state |
| `bind_port(port)` | Set by the orchestrator once the gateway port is known |
| `status()` | Dict for `EphemeralMockServer.status` |
| `register_routes(app)` | **Abstract** — must mount FastAPI routes |
| `on_start()` / `on_stop()` | Lifecycle hooks (override for warm-up / flush) |
| `reset()` | **Abstract** — wipe in-memory state |

## Known caveats

- `name` is a *class* attribute; subclasses should override it
  rather than setting it in `__init__`, so the `status()` dict
  always shows the right value.
- The base class is not directly instantiable; `register_routes`
  and `reset` are abstract.
- `status()` returns `port=self._port`, which is `None` until
  `bind_port` has been called by the orchestrator.
