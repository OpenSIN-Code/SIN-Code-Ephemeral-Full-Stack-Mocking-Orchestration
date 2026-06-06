# `http_mock.py` — FastAPI HTTP Mock

What: Builds a FastAPI application with dynamically-registered routes from a
config list, then starts uvicorn in a background process.

Dependencies: `fastapi`, `uvicorn`

Usage:
```python
from efm.http_mock import build_app
app = build_app([{"path": "/ping", "method": "GET", "response": "pong"}])
```

Caveats: Route functions are created via closure; the background process
reads route definitions from a temporary JSON file to avoid serialising
closures across a fork.
