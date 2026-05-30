"""Orchestriert Mock-Server, DB und Sandbox für einen Agent-Task."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .mock_generator import MockServer, StatefulMock
from .sandbox import DockerSandbox


@dataclass
class TestEnvironment:
    mock_port: int
    db_dsn: str | None
    container_id: str | None
    env_vars: dict[str, str] = field(default_factory=dict)


class EphemeralOrchestrator:
    """Baut eine vollständige Testumgebung für einen Agent-Task."""

    def __init__(self):
        self.mock_server = MockServer()
        self.sandbox = DockerSandbox()
        self._mock_port = 8787

    def configure_from_task(self, task_context: dict) -> TestEnvironment:
        """
        task_context: dict with keys:
            - name: str
            - external_apis: list[str]  # e.g., ["stripe", "github"]
            - requires_db: bool
            - test_command: str
        """
        env_vars = {}
        for api in task_context.get("external_apis", []):
            mock = StatefulMock(
                name=api,
                base_path=f"/{api}",
                scenarios={},
            )
            self.mock_server.add_mock(mock)
            env_vars[f"{api.upper()}_BASE_URL"] = f"http://host.docker.internal:{self._mock_port}/{api}"

        db_dsn = None
        if task_context.get("requires_db"):
            db_dsn = "sqlite:///:memory:"
            env_vars["DATABASE_URL"] = db_dsn

        return TestEnvironment(
            mock_port=self._mock_port,
            db_dsn=db_dsn,
            container_id=None,
            env_vars=env_vars,
        )

    def run_tests(self, test_command: str, with_network: bool = True) -> dict:
        try:
            if with_network:
                result = self.sandbox.run_with_network(test_command, timeout=120)
            else:
                result = self.sandbox.run_command(test_command, timeout=120)
            return {
                "exit_code": result.exit_code,
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:2000],
                "success": result.exit_code == 0,
            }
        except Exception as e:
            return {"exit_code": -1, "stdout": "", "stderr": str(e), "success": False}
