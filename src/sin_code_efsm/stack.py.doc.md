# stack.py

Convenience container that bundles the five default services.

## What it does

`FullStack` instantiates the five default mock services
(`HTTPService`, `DatabaseService`, `AuthService`, `QueueService`,
`StorageService`) in one object. Used by `EphemeralMockServer`
when the caller passes `services=None` (i.e. wants everything).

## Dependencies

- `services/` — each default service class

## Public API

| Symbol | Purpose |
|--------|---------|
| `FullStack` | Container with `.http`, `.database`, `.auth`, `.queue`, `.storage` |
| `FullStack.as_dict()` | Returns the same services as a `{name: service}` dict |
| `FullStack.reset_all()` | Reset every service (database also drops its schema) |

## Known caveats

- `reset_all()` is destructive: `DatabaseService.hard_reset()` drops
  the schema, not just the rows. Use `reset()` per-service if you
  want to preserve the schema.
- The class does not enforce any particular lifecycle; the
  orchestrator drives `on_start` / `on_stop` / `reset`.
