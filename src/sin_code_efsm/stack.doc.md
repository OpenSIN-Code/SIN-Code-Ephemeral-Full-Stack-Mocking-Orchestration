# `stack.py` — Stack Configuration

What this file does: defines the default service stack and port allocation for ephemeral environments.

## Dependencies

- Imported by: `orchestrator.py`, `server.py`

## Public API

- `DEFAULT_STACK` — list of default services to start
- `allocate_port(preferred)` — find an available port

## Notes

Port allocation tries the preferred port first, then scans upward.
