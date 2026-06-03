# mock_generator.py

Stateful mock server and per-resource in-memory state.

## What it does

Two cooperating classes:

- `StatefulMock` — one resource with `state` (the in-memory record)
  and `scenarios` (canned responses keyed by `METHOD:path`).
- `MockServer` — registry of `StatefulMock`s plus a FastAPI gateway
  and an in-process `dispatch()` for tests.

## Dependencies

- `fastapi` — required only for the HTTP gateway (`app` / `run`)
- `uvicorn` — required only for `run()`

## Public API

| Symbol | Purpose |
|--------|---------|
| `StatefulMock` | Dataclass: name, base_path, state, scenarios |
| `StatefulMock.respond(method, path, body)` | Default CRUD dispatch |
| `MockServer` | Registry + dispatcher + FastAPI gateway |
| `MockServer.add_mock(mock)` | Register a `StatefulMock` under `base_path` |
| `MockServer.dispatch(method, path, body)` | In-process route (no HTTP) |
| `MockServer.app` | Lazy-built FastAPI app |
| `MockServer.run(host, port)` | Serve via uvicorn |

## Default CRUD dispatch

`StatefulMock.respond` without a scenario match:

| Method | Behavior |
|--------|----------|
| POST | Append `body` to `state[resource]` list, return `{status, id, data}` |
| GET | Return `state[resource]` (or `[]`) |
| DELETE | Drop `state[resource]`, return `{status, resource}` |
| PUT / PATCH | Replace `state[resource] = body`, return `{status, data}` |

## Usage

```python
from sin_code_efsm.mock_generator import MockServer, StatefulMock
ms = MockServer()
ms.add_mock(StatefulMock(name="users", base_path="/users"))
print(ms.dispatch("GET", "/users"))
```

## Known caveats

- The in-memory state is process-local; multiple `MockServer`
  instances do not share state.
- The FastAPI gateway uses a catch-all `/{path:path}` route, so
  static assets and non-mock paths return 404 from the gateway.
- `app` is lazily built to avoid forcing `fastapi` on callers who
  only need `dispatch()` for tests.
