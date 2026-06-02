# `base.py` — Base Service

What this file does: abstract base class for all ephemeral mock services (HTTP, DB, Auth, Queue, Storage).

## Dependencies

- Imported by: all services in `services/`

## Public API

- `BaseService(prefix)` — base class with `start()`, `stop()`, `reset()` methods

## Notes

All services register routes under a common prefix in the FastAPI app.
