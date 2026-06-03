# services/http.py

HTTP endpoint mocking service.

## What it does

Lets you register arbitrary REST endpoints that the shared gateway
serves under `/http/*`. Unregistered paths return 404 with
`{"error": "endpoint not registered", "path": "..."}` so callers
can distinguish "I forgot to register this" from a real outage.

Every request is recorded in a call log (`calls()`) so tests can
assert on what was hit, with what body, in what order.

## Dependencies

- `threading` (stdlib) for the call-log lock
- `fastapi`
- `state.py` — `StateStore` (endpoint registry)

## Public API

| Symbol | Purpose |
|--------|---------|
| `HTTPService` | The service class (`name="http"`, `prefix="/http"`) |
| `add_endpoint(method, path, response, status_code=200)` | Register a mock |
| `get_endpoint(method, path)` | Return registered config or `None` |
| `remove_endpoint(method, path)` | Remove a registration |
| `endpoints()` | List all `(method, path)` tuples |
| `calls()` / `clear_calls()` | Access / clear the request log |

## Valid HTTP methods

`_VALID_METHODS` is the closed set: `GET`, `POST`, `PUT`, `PATCH`,
`DELETE`, `HEAD`, `OPTIONS`. Anything else raises `ValueError`.

## Usage

```python
from sin_code_efsm.services.http import HTTPService
http = HTTPService()
http.add_endpoint("GET", "/users/1", {"id": 1, "name": "Ada"})
print(http.calls())  # recorded requests so far
```

## Known caveats

- Endpoint keys are normalized to `METHOD::/path` (uppercase
  method, leading-slash path). Registering the same key twice
  overwrites the first registration — there is no warning.
- The call log is unbounded. For long-running tests, call
  `clear_calls()` between phases or risk memory growth.
- `register_routes` uses a catch-all `/{path:path}` so non-mock
  paths under `/http/...` are 404, not 405.
