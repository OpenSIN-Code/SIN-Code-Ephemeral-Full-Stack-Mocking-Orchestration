# mcp_server.py

FastMCP server for agent integration.

## What it does

Wraps `MockGenerator` and `MockOrchestrator` in a `FastMCP` server
so agents (opencode, claude-code) can generate and orchestrate
mocks over the Model Context Protocol.

## Dependencies

- `orchestrator.py` — `MockOrchestrator`
- `mock_generator.py` — `MockGenerator`
- `mcp.server.fastmcp.FastMCP` — optional; soft import

## Tools

| Tool | Returns | Description |
|------|---------|-------------|
| `generate_mock(service_spec, format="json")` | JSON | Generate a mock from an OpenAPI/GraphQL spec |
| `orchestrate_mock(services, scenario="default")` | JSON | Orchestrate ephemeral mocks for integration testing |

## Usage

```bash
python -m sin_code_efsm.mcp_server
```

In `opencode.json` configure the MCP server; the tools become
available to agents.

## Known caveats

- Requires `pip install 'sin-code-efsm[mcp]'` for the `mcp` package.
- Each tool call re-creates its generator/orchestrator from scratch;
  no in-memory caching across calls.
