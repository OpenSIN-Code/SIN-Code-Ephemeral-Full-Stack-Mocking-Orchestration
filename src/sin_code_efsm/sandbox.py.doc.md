# sandbox.py

Docker-based sandbox with a subprocess fallback.

## What it does

`DockerSandbox` runs user-supplied shell commands in an isolated
container (512 MB memory limit, `bridge` or `none` network mode).
When no Docker daemon is reachable, it transparently falls back to
`subprocess.run` — with a `backend="subprocess"` marker on the
returned `SandboxResult` so callers can detect the degraded mode.

## Dependencies

- `docker` (Python SDK) — required for the Docker backend only
- `subprocess` (stdlib) — for the fallback path

## Public API

| Symbol | Purpose |
|--------|---------|
| `SandboxResult` | Dataclass: exit_code, stdout, stderr, container_id, backend |
| `docker_available()` | True if a Docker daemon is reachable |
| `DockerSandbox(base_image, allow_fallback)` | The sandbox class |
| `DockerSandbox.run_command(cmd, timeout, network, extra_hosts)` | Run a shell command |

## Defaults

| Constant | Value | Why |
|----------|-------|-----|
| `base_image` | `python:3.11-slim` | Small, ubiquitous, fast cold start |
| `mem_limit` | `"512m"` | Caps a runaway agent at 512 MB |
| `network_mode` | `none` (default), `bridge` if `network=True` | Locked down by default |

## Usage

```python
from sin_code_efsm.sandbox import DockerSandbox
sb = DockerSandbox()
result = sb.run_command("pytest -q", timeout=120, network=True)
assert result.exit_code == 0
```

## Known caveats

- The fallback subprocess runs as the current user with no UID/GID
  isolation. Treat any data it produces as untrusted.
- The container is removed (`force=True`) in the `finally` block;
  orphaned containers from a crashed sandbox are still possible.
- `extra_hosts={"host.docker.internal": "host-gateway"}` is the
  standard Docker Desktop trick for reaching the host network.
