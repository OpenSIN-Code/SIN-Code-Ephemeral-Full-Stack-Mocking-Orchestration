from sin_code_efsm.orchestrator import EphemeralOrchestrator


def test_orchestrator():
    orch = EphemeralOrchestrator()
    env = orch.configure_from_task({
        "name": "test",
        "external_apis": ["stripe"],
        "requires_db": False,
    })
    assert env.mock_port == 8787
    assert "STRIPE_BASE_URL" in env.env_vars
