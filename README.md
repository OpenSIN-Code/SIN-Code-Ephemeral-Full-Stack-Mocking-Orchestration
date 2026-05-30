# SIN-Code Ephemeral Full-Stack Mocking Orchestration (EFSM)

Builds a complete, isolated test environment with stateful mocks for every agent task.

## Features
- FastAPI-based stateful mock servers
- Docker sandbox for isolated execution
- Ephemeral orchestration per task
- SQLite in-memory database support
- Network-isolated containers

## Install
```bash
pip install -e .
```

## Usage
```bash
efsm setup my-test --api stripe --api github --db --test-cmd pytest
```

## Architecture
- `MockServer`: FastAPI app with catch-all routing to registered mocks
- `StatefulMock`: Per-API stateful mock with configurable scenarios
- `DockerSandbox`: Containerized test execution with resource limits
- `EphemeralOrchestrator`: Combines all pieces for a single task
