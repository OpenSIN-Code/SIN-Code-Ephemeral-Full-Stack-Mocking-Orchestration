# http.py.doc.md

**What this file does:** `HTTPService` mocks arbitrary REST endpoints under the
`/http` prefix on the shared FastAPI gateway.

## Dependencies

- `fastapi.Request`, `JSONResponse` — imported at module level so FastAPI
  correctly resolves the `Request` type annotation for dependency injection.
  (Local imports inside `register_routes` caused 422 errors because FastAPI
  treated `request` as a query parameter.)

## Important config values

- `_VALID_METHODS` = `GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS`
- `prefix = "/http"` — all mock endpoints are served under this path.

## Key design decisions

- **Thread-safe endpoint store** — `StateStore` (from `state.py`) wraps a `dict`
  with a `threading.Lock` so multiple concurrent requests can register and hit
  endpoints safely.
- **Call log** — every request is recorded in `self._call_log` so tests can
  assert on side-effects (e.g. "was the webhook called?").
- **404 for unregistered paths** — distinguishes "forgot to register" from real
  outages.

## Usage examples

```python
http = HTTPService()
http.add_endpoint("GET", "/users/1", {"id": 1, "name": "Ada"})
```

## Known caveats

- The `path:path` route parameter in FastAPI captures everything including
  slashes, so `/http/a/b/c` works as expected.
