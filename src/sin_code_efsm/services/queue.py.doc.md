# services/queue.py

In-memory pub/sub message queue mock.

## What it does

Stores messages per topic in a dict-of-lists. The shared gateway
exposes:

- `POST /queue/publish/{topic}` — append a JSON message
- `GET  /queue/consume/{topic}` — read up to N messages
- `GET  /queue/topics` — list topic names

`reset()` wipes every topic. There is no per-topic TTL, no
max-length cap, and no at-most-once delivery guarantee.

## Dependencies

- `threading` (stdlib) for the topics lock
- `fastapi`

## Public API

| Symbol | Purpose |
|--------|---------|
| `QueueService` | The service class (`name="queue"`, `prefix="/queue"`) |
| `publish(topic, message)` | Append a message; return new topic count |
| `consume(topic, limit=10)` | Read up to `limit` messages (peek, no pop) |
| `topics()` | List topic names |
| `reset()` | Wipe everything |

## Usage

```python
from sin_code_efsm.services.queue import QueueService
q = QueueService()
q.publish("orders", {"id": 1, "total": 9.99})
print(q.consume("orders"))
```

## Known caveats

- `consume` does NOT remove messages; it peeks. Add an explicit
  `pop` if your test needs at-most-once semantics.
- The dict-of-lists grows without bound until `reset()`.
- Concurrent `publish` / `consume` is safe (lock-protected), but
  ordering is only guaranteed per-topic.
