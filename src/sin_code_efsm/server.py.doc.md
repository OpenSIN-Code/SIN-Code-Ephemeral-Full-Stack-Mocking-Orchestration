# server.py.doc.md

**What this file does:** Main `EphemeralMockServer` class that spins up a complete
ephemeral mock stack on a single FastAPI gateway.

## Dependencies

- `fastapi` — shared HTTP gateway
- `uvicorn` — ASGI server
- `sin_code_efsm.services.*` — individual mock services
- `sin_code_efsm.stack.FullStack` — convenience composition container
- `sin_code_efsm.state.StateManager` — thread-safe status tracking

## Important config values

- `_ALL_SERVICES` = `("http", "database", "auth", "queue", "storage")` — default
  services when `services=None`.
- `port=8888` — default preferred port. Falls back to any free port if occupied.

## Key design decisions

- **No `_find_free_port()`** — we create a bound socket ourselves with
  `SO_REUSEADDR`, bind to the preferred port (or `0` if occupied), and pass that
  socket directly to Uvicorn via `server.run(sockets=[sock])`. This eliminates the
  classic race condition where a port is free during the check but taken by the
  time Uvicorn binds.
- **Signal handlers** are installed only when running in the main thread
  (`ValueError` is caught and ignored otherwise).
- **Graceful shutdown** — `stop()` calls `on_stop()` on every service, then
  `should_exit=True`, joins the thread, and closes the socket.

## Usage examples

```python
from sin_code_efsm import EphemeralMockServer
server = EphemeralMockServer(port=8888)
server.start()
print(server.url)   # "http://127.0.0.1:8888" (or different port)
server.stop()
```

## Known caveats

- Fast startup depends on `uvicorn` using `uvloop` on Linux/macOS. On Windows the
  loop factory is different but still well under 2 seconds.
- `add_endpoint` raises `RuntimeError` if the HTTP service is not enabled.
