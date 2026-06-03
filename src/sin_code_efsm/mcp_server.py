"""MCP server for agent integration.

Docs: mcp_server.py.doc.md
"""
from __future__ import annotations

import json

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    # Soft import so the rest of the package remains usable without
    # the MCP dependency installed; `main()` raises a clear error
    # at runtime instead.
    FastMCP = None

from .orchestrator import MockOrchestrator
from .mock_generator import MockGenerator


# Server identity reported to MCP clients in the initialize handshake.
_SERVER_NAME = "sin-code-efsm"
_DEFAULT_MOCK_FORMAT = "json"
_DEFAULT_SCENARIO = "default"


def main():
    """Build the FastMCP server and start it on stdio (blocks).

    Raises:
        RuntimeError: If the optional `mcp` package is not installed.
    """
    if FastMCP is None:
        raise RuntimeError("mcp package not installed. Install with: pip install 'sin-code-efsm[mcp]'")

    mcp = FastMCP(_SERVER_NAME)

    @mcp.tool()
    def generate_mock(service_spec: str, format: str = _DEFAULT_MOCK_FORMAT) -> str:
        """Generate a mock service from an OpenAPI or GraphQL spec.

        Args:
            service_spec: Path to the spec file or its inline content.
            format: Output format (`json` today; YAML may be added later).

        Returns:
            JSON-encoded mock definition.
        """
        generator = MockGenerator()
        return json.dumps(generator.generate(service_spec, format=format), indent=2)

    @mcp.tool()
    def orchestrate_mock(services: list, scenario: str = _DEFAULT_SCENARIO) -> str:
        """Orchestrate ephemeral mock services for integration testing.

        Args:
            services: List of service descriptors (names, configs).
            scenario: Named scenario preset.

        Returns:
            JSON-encoded orchestration plan.
        """
        orch = MockOrchestrator()
        return json.dumps(orch.orchestrate(services, scenario=scenario), indent=2)

    mcp.run()


if __name__ == "__main__":
    main()
