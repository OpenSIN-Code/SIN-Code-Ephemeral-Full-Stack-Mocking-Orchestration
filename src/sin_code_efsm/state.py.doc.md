# state.py

Thread-safe state containers for the mock stack.

## What it does

Two small classes:

- `StateManager` — registry of `ServiceRecord`s (one per service),
  with status / port / error tracking. Thread-safe via a `Lock`.
- `StateStore` — thread-safe key-value store with a reset method.
  Used as the backing store for service-local data (e.g. registered
  HTTP endpoints, in-memory users).

## Dependencies

- (none — stdlib `threading` + dataclasses)

## Public API

### `StateManager`

| Method | Purpose |
|--------|---------|
| `register(name, port)` | Create (or fetch) a `ServiceRecord` |
| `set_service(name, svc)` | Attach the live service instance |
| `set_status(name, status)` | Update lifecycle state (`up` / `down` / ...) |
| `set_error(name, error)` | Mark the service as `error` |
| `clear(name)` | Reset one record to defaults |
| `get(name)` | Fetch one record (no lock — for read-only consumers) |
| `all()` / `all_up()` | Snapshots / filters |
| `drop()` | Wipe every record |

### `StateStore`

| Method | Purpose |
|--------|---------|
| `set(key, value)` / `get(key)` / `delete(key)` | Standard kv |
| `keys()` | Snapshot of all keys |
| `reset()` | Clear all data |

## Known caveats

- `get()` on `StateManager` does not take the lock; it is only safe
  to call from the thread that owns the write side, or to treat the
  result as a snapshot that may go stale immediately.
- `StateStore.get` does take the lock but returns the raw value
  (not a deep copy); mutating it in place is a race.
