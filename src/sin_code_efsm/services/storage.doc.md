# `storage.py` — Storage Mock Service

What this file does: dict-based S3-like object store for simulating cloud storage.

## Dependencies

- Imported by: `server.py`, tests
- Imports: `base` (BaseService)

## Public API

- `StorageService(prefix="/storage")` — mock storage service
- `put(key, data)` — store an object
- `get(key)` — retrieve an object
- `delete(key)` — remove an object
- `list(prefix)` — list keys matching a prefix

## Usage

```python
from sin_code_efsm.services.storage import StorageService
storage = StorageService()
storage.put("avatars/user-123.png", b"...")
```

## Notes

Objects are stored in memory. No actual file I/O is performed.
