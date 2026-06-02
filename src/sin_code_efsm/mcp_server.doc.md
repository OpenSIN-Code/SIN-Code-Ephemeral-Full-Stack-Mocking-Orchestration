# `mcp_server.py` — MCP Server for EFSM

What this file does: exposes ephemeral mock orchestration tools to AI agents via the Model Context Protocol.

## Dependencies

- Imported by: CLI, external MCP hosts
- Imports: `orchestrator` (MockOrchestrator), `mock_generator` (MockGenerator)

## Tools

- `generate_mock(service_spec, format="json")` — generate a mock service from an OpenAPI or GraphQL spec
- `orchestrate_mock(services, scenario="default")` — orchestrate ephemeral mock services for integration testing

## Usage

```bash
python -m sin_code_efsm.mcp_server
```

Requires `pip install -e ".[mcp]"`.

## Notes

Uses `mcp.server.fastmcp.FastMCP` for tool registration.
