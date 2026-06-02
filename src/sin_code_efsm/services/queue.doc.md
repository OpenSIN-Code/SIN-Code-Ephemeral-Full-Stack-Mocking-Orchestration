# `queue.py` — Queue Mock Service

What this file does: in-memory pub/sub per topic for simulating message queues.

## Dependencies

- Imported by: `server.py`, tests
- Imports: `base` (BaseService)

## Public API

- `QueueService(prefix="/queue")` — mock queue service
- `publish(topic, message)` — send a message to a topic
- `subscribe(topic)` — return all messages for a topic

## Usage

```python
from sin_code_efsm.services.queue import QueueService
queue = QueueService()
queue.publish("orders", {"id": 1, "item": "coffee"})
```

## Notes

Messages are stored in-memory per topic. No persistence across restarts.
