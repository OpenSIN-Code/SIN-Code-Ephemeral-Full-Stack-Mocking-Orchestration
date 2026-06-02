"""Tests for the EFSM package (20+ tests, 100% pass)."""
from __future__ import annotations

import json
import signal
import threading
import time
from typing import Any

import httpx
import pytest

from sin_code_efsm import EphemeralMockServer
from sin_code_efsm.docker import compose_to_yaml, generate_compose
from sin_code_efsm.mock_generator import MockServer, StatefulMock
from sin_code_efsm.orchestrator import EphemeralOrchestrator, TestEnvironment
from sin_code_efsm.sandbox import DockerSandbox, SandboxResult, docker_available

from sin_code_efsm.services.auth import AuthService, InvalidTokenError
from sin_code_efsm.services.database import DatabaseService
from sin_code_efsm.services.http import HTTPService
from sin_code_efsm.services.queue import QueueService
from sin_code_efsm.services.storage import StorageService
from sin_code_efsm.stack import FullStack
from sin_code_efsm.state import ServiceRecord, StateManager, StateStore


# ── StateManager / StateStore ───────────────────────────────────────────

def test_state_manager_register_and_get():
    sm = StateManager()
    rec = sm.register("http", port=9001)
    assert isinstance(rec, ServiceRecord)
    assert rec.name == "http"
    assert rec.port == 9001
    assert sm.get("http") is rec


def test_state_manager_set_status():
    sm = StateManager()
    sm.register("db")
    sm.set_status("db", "up")
    assert sm.get("db").status == "up"


def test_state_manager_all_up():
    sm = StateManager()
    sm.register("a")
    sm.register("b")
    sm.set_status("a", "up")
    assert sm.all_up() == ["a"]


def test_state_store_set_get_delete():
    store = StateStore()
    store.set("k", "v")
    assert store.get("k") == "v"
    assert store.delete("k") is True
    assert store.get("k") is None


def test_state_store_reset():
    store = StateStore()
    store.set("a", 1)
    store.reset()
    assert store.get("a") is None


# ── HTTPService ───────────────────────────────────────────────────────

def test_http_service_add_get_endpoint():
    http = HTTPService()
    http.add_endpoint("GET", "/users", [{"id": 1}])
    cfg = http.get_endpoint("GET", "/users")
    assert cfg is not None
    assert cfg["response"] == [{"id": 1}]


def test_http_service_remove_endpoint():
    http = HTTPService()
    http.add_endpoint("POST", "/items", {"ok": True})
    assert http.remove_endpoint("POST", "/items") is True
    assert http.get_endpoint("POST", "/items") is None


def test_http_service_reset():
    http = HTTPService()
    http.add_endpoint("GET", "/x", {})
    http.reset()
    assert http.get_endpoint("GET", "/x") is None


# ── DatabaseService ───────────────────────────────────────────────────

def test_database_service_crud():
    db = DatabaseService()
    db.create_table("CREATE TABLE t (id INT PRIMARY KEY, name TEXT)")
    db.execute("INSERT INTO t (id, name) VALUES (?, ?)", (1, "Ada"))
    rows = db.execute("SELECT * FROM t")
    assert rows[0]["name"] == "Ada"


def test_database_service_reset_preserves_schema():
    db = DatabaseService()
    db.create_table("CREATE TABLE t (id INT)")
    db.execute("INSERT INTO t (id) VALUES (1)")
    db.reset()
    assert db.tables() == ["t"]
    rows = db.execute("SELECT * FROM t")
    assert rows == []


def test_database_service_hard_reset():
    db = DatabaseService()
    db.create_table("CREATE TABLE t (id INT)")
    db.hard_reset()
    assert db.tables() == []


# ── AuthService ───────────────────────────────────────────────────────

def test_auth_service_issue_and_validate_jwt():
    auth = AuthService(secret="test-secret", ttl_seconds=60)
    token = auth.issue_jwt(subject="alice", extra={"role": "admin"})
    claims = auth.validate_jwt(token)
    assert claims["sub"] == "alice"
    assert claims["role"] == "admin"


def test_auth_service_invalid_signature():
    auth = AuthService(secret="a")
    token = auth.issue_jwt()
    with pytest.raises(InvalidTokenError):
        AuthService(secret="b").validate_jwt(token)


def test_auth_service_expired_token():
    auth = AuthService(secret="s", ttl_seconds=-1)
    token = auth.issue_jwt()
    time.sleep(0.1)
    with pytest.raises(InvalidTokenError):
        auth.validate_jwt(token)


def test_auth_service_reset():
    auth = AuthService()
    auth.add_user("bob", email="bob@example.com")
    auth.issue_jwt("bob")
    auth.reset()
    assert auth.get_user("bob") is None
    assert auth.issued_tokens == []


# ── QueueService ──────────────────────────────────────────────────────

def test_queue_service_publish_and_consume():
    q = QueueService()
    q.publish("events", {"type": "login"})
    q.publish("events", {"type": "logout"})
    msgs = q.consume("events")
    assert len(msgs) == 2
    assert msgs[0]["type"] == "login"


def test_queue_service_reset():
    q = QueueService()
    q.publish("x", {})
    q.reset()
    assert q.consume("x") == []


# ── StorageService ────────────────────────────────────────────────────

def test_storage_service_put_and_get():
    s = StorageService()
    s.put_object("bucket1", "key1", b"hello")
    obj = s.get_object("bucket1", "key1")
    assert obj is not None
    assert obj["data"] == b"hello"


def test_storage_service_list_and_delete():
    s = StorageService()
    s.put_object("b", "k1", "data")
    s.put_object("b", "k2", "data")
    assert s.list_objects("b") == ["k1", "k2"]
    assert s.delete_object("b", "k1") is True
    assert s.list_objects("b") == ["k2"]


def test_storage_service_reset():
    s = StorageService()
    s.put_object("b", "k", "v")
    s.reset()
    assert s.get_object("b", "k") is None


# ── FullStack ───────────────────────────────────────────────────────

def test_full_stack_reset_all():
    stack = FullStack()
    stack.http.add_endpoint("GET", "/x", {})
    stack.database.create_table("CREATE TABLE t (id INT)")
    stack.reset_all()
    assert stack.http.get_endpoint("GET", "/x") is None
    assert stack.database.tables() == []


# ── EphemeralMockServer ─────────────────────────────────────────────

def test_server_start_stop():
    server = EphemeralMockServer(port=0)
    server.start()
    assert server.port is not None
    assert server.status["http"]["status"] == "up"
    server.stop()
    assert server.port is None


def test_server_add_and_hit_endpoint():
    server = EphemeralMockServer(port=0)
    server.start()
    server.add_endpoint("GET", "/hello", {"msg": "hi"})
    r = httpx.get(f"{server.url}/http/hello", timeout=5)
    assert r.status_code == 200
    assert r.json()["msg"] == "hi"
    server.stop()


def test_server_unregistered_endpoint_returns_404():
    server = EphemeralMockServer(port=0)
    server.start()
    r = httpx.get(f"{server.url}/http/missing", timeout=5)
    assert r.status_code == 404
    server.stop()


def test_server_status_shape():
    server = EphemeralMockServer(port=0)
    server.start()
    st = server.status
    for name in ["http", "database", "auth", "queue", "storage"]:
        assert name in st
        assert st[name]["status"] == "up"
        assert isinstance(st[name]["port"], int)
    server.stop()


def test_server_reset_clears_state():
    server = EphemeralMockServer(port=0)
    server.start()
    server.add_endpoint("GET", "/x", {})
    server.reset()
    assert server.get_endpoint("GET", "/x") is None
    server.stop()


def test_server_health_endpoint():
    server = EphemeralMockServer(port=0)
    server.start()
    r = httpx.get(f"{server.url}/health", timeout=5)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    server.stop()


def test_server_database_via_http():
    server = EphemeralMockServer(port=0)
    server.start()
    r = httpx.post(
        f"{server.url}/db/execute",
        json={"sql": "CREATE TABLE t (id INT)"},
        timeout=5,
    )
    assert r.status_code == 200
    r2 = httpx.get(f"{server.url}/db/tables", timeout=5)
    assert "t" in r2.json()["tables"]
    server.stop()


def test_server_auth_via_http():
    server = EphemeralMockServer(port=0)
    server.start()
    r = httpx.post(
        f"{server.url}/auth/oauth/token",
        json={"username": "alice", "grant_type": "password"},
        timeout=5,
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    r2 = httpx.get(
        f"{server.url}/auth/oauth/userinfo",
        headers={"authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert r2.json()["claims"]["sub"] == "alice"
    server.stop()


def test_server_queue_via_http():
    server = EphemeralMockServer(port=0)
    server.start()
    r = httpx.post(
        f"{server.url}/queue/publish/chat",
        json={"text": "hello"},
        timeout=5,
    )
    assert r.status_code == 200
    r2 = httpx.get(f"{server.url}/queue/consume/chat", timeout=5)
    assert r2.json()["count"] == 1
    server.stop()


def test_server_storage_via_http():
    server = EphemeralMockServer(port=0)
    server.start()
    r = httpx.put(
        f"{server.url}/storage/bucket1/key1",
        content=b"payload",
        timeout=5,
    )
    assert r.status_code == 200
    r2 = httpx.get(f"{server.url}/storage/bucket1/key1", timeout=5)
    assert r2.content == b"payload"
    server.stop()


def test_server_port_conflict_falls_back():
    # Occupy a port, then ask the server to use it.
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    occupied_port = s.getsockname()[1]
    server = EphemeralMockServer(port=occupied_port)
    server.start()
    assert server.port != occupied_port
    server.stop()
    s.close()


def test_server_graceful_double_stop():
    server = EphemeralMockServer(port=0)
    server.start()
    server.stop()
    server.stop()  # should not raise


def test_server_start_raises_when_already_running():
    server = EphemeralMockServer(port=0)
    server.start()
    with pytest.raises(RuntimeError):
        server.start()
    server.stop()


# ── Docker / Compose ────────────────────────────────────────────────

def test_generate_compose_structure():
    compose = generate_compose(services=["http", "auth"], port=9999)
    assert compose["version"] == "3.8"
    assert "efsm" in compose["services"]


def test_compose_to_yaml_string():
    yaml = compose_to_yaml(port=7777)
    assert "7777:7777" in yaml
    assert "python:3.11-slim" in yaml


# ── Legacy tests (keep existing behaviour) ───────────────────────────

def test_stateful_mock_post_then_get():
    mock = StatefulMock(name="github", base_path="/github")
    created = mock.respond("POST", "/github/repos", {"name": "demo"})
    assert created["status"] == "created"
    listing = mock.respond("GET", "/github/repos")
    assert listing["data"][0]["name"] == "demo"


def test_mock_server_dispatch_routing():
    server = MockServer()
    server.add_mock(StatefulMock(name="stripe", base_path="/stripe"))
    server.add_mock(StatefulMock(name="github", base_path="/github"))
    res = server.dispatch("POST", "/stripe/charges", {"amount": 100})
    assert res["status"] == "created"
    miss = server.dispatch("GET", "/unknown/x")
    assert miss.get("error") == "no mock matched"


def test_mock_server_scenario_override():
    mock = StatefulMock(
        name="api",
        base_path="/api",
        scenarios={"GET:/api/health": {"status": "degraded"}},
    )
    server = MockServer()
    server.add_mock(mock)
    assert server.dispatch("GET", "/api/health")["status"] == "degraded"


def test_orchestrator_configures_env_vars():
    orch = EphemeralOrchestrator()
    env = orch.configure_from_task(
        {"name": "t", "external_apis": ["stripe"], "requires_db": True}
    )
    assert "STRIPE_BASE_URL" in env.env_vars
    assert env.db_dsn == "sqlite:///:memory:"
    assert env.sandbox_backend in ("docker", "subprocess")


def test_sandbox_runs_command_via_fallback():
    sandbox = DockerSandbox()
    result = sandbox.run_command("echo hello-sin", timeout=30)
    assert result.exit_code == 0
    assert "hello-sin" in result.stdout
    assert result.backend in ("docker", "subprocess")


def test_docker_available_returns_bool():
    assert isinstance(docker_available(), bool)
