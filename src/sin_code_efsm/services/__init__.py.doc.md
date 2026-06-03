# services/__init__.py

Mock services package.

## What it does

Re-exports the five default services (`BaseService`, `HTTPService`,
`DatabaseService`, `AuthService`, `QueueService`, `StorageService`)
so callers can do `from sin_code_efsm.services import HTTPService`.

## Public exports

| Symbol | Source |
|--------|--------|
| `BaseService` | `base.py` |
| `HTTPService` | `http.py` |
| `DatabaseService` | `database.py` |
| `AuthService` | `auth.py` |
| `QueueService` | `queue.py` |
| `StorageService` | `storage.py` |

## Known caveats

- `BaseService` is an `ABC`; instantiating it directly raises
  `TypeError` because `register_routes` and `reset` are abstract.
