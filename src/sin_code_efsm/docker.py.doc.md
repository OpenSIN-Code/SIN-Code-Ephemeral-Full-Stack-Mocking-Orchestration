# docker.py

Docker Compose generation helpers (no daemon required).

## What it does

Builds a minimal `docker-compose.yml` for the EFSM stack — useful
for local development against a real Docker daemon. Two forms:

- `generate_compose(...)` → `dict` (call `yaml.dump` if you have PyYAML)
- `compose_to_yaml(...)` → `str` (no PyYAML required)

## Dependencies

- (none — pure data construction)

## Public API

| Function | Returns | Use case |
|----------|---------|----------|
| `generate_compose(services, port)` | `dict` | Programmatic use |
| `compose_to_yaml(services, port)` | `str` | Drop into a repo |

## Defaults

- `services` defaults to all five: `http`, `database`, `auth`, `queue`, `storage`
- `port` defaults to 8888
- Image is `python:3.11-slim`; command is `python -m sin_code_efsm.server`

## Usage

```python
from sin_code_efsm.docker import compose_to_yaml
with open("docker-compose.yml", "w") as f:
    f.write(compose_to_yaml())
```

## Known caveats

- The compose file is intentionally minimal; production deployments
  will need healthchecks, volumes, and secrets configured.
- The container runs as the default `python` user (non-root) but
  with full capabilities — tighten for untrusted workloads.
