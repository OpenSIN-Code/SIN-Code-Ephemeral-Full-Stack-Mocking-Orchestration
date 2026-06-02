# `http.py` — HTTP Mock Service

What this file does: mock REST endpoints with per-method registration and stateful responses.

## Dependencies

- Imported by: `server.py`, tests
- Imports: `base` (BaseService)

## Public API

- `HTTPService(prefix="/http")` — mock HTTP service
- `add_endpoint(method, path, response)` — register a mock endpoint
- `get_request_log()` — history of received requests

## Usage

```python
from sin_code_efsm.services.http import HTTPService
http = HTTPService()
http.add_endpoint("GET", "/hello", {"msg": "world"})
```

## Notes

Responses can be static dicts or callable functions for dynamic behavior.
