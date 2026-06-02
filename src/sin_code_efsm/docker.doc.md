# `docker.py` — Docker Sandbox

What this file does: Docker-based sandbox for running tests with stronger isolation.

## Dependencies

- Imported by: `orchestrator.py`, tests

## Public API

- `DockerSandbox(image)` — create a sandbox
- `run(command)` — execute a command in the container
- `available()` — check if Docker is installed

## Notes

Falls back to subprocess runner when Docker is not available.
