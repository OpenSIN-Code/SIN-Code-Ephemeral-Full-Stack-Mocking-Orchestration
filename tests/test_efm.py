"""Tests for the EFM CLI and core modules.

Docs: test_efm.doc.md
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from efm.config import load_config, validate_config
from efm.http_mock import build_app
from efm.db_mock import start_sqlite_mock, get_connection, stop_sqlite_mock
from efm.process import write_pid, read_pid, is_running, stop_all, list_running, PID_DIR

FIXTURES = Path(__file__).with_name("fixtures")
CONFIG_PATH = FIXTURES / "mock_config.yaml"


class TestConfig:
    """Config parsing and validation."""

    def test_load_config_yaml(self):
        cfg = load_config(CONFIG_PATH)
        assert "services" in cfg
        assert len(cfg["services"]) == 2

    def test_validate_config_ok(self):
        cfg = load_config(CONFIG_PATH)
        validate_config(cfg)  # should not raise

    def test_validate_config_missing_services(self):
        with pytest.raises(ValueError, match="services"):
            validate_config({})


class TestHTTPMock:
    """HTTP mock lifecycle."""

    def test_build_app_has_routes(self):
        routes = [
            {"path": "/users", "method": "GET", "response": '{"users": []}'},
            {"path": "/health", "method": "GET", "response": "ok"},
        ]
        app = build_app(routes)
        assert len(app.routes) >= 2  # FastAPI includes default /docs etc.

    def test_http_mock_response_json(self):
        routes = [
            {"path": "/users", "method": "GET", "response": '{"users": [{"id": 1, "name": "Alice"}]}'},
        ]
        from fastapi.testclient import TestClient
        app = build_app(routes)
        client = TestClient(app)
        resp = client.get("/users")
        assert resp.status_code == 200
        assert resp.json() == {"users": [{"id": 1, "name": "Alice"}]}


class TestDBMock:
    """SQLite mock lifecycle."""

    def test_start_sqlite_mock(self):
        db_path = start_sqlite_mock(
            "test-users",
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);",
            ["INSERT INTO users (id, name) VALUES (1, 'Alice');"],
        )
        assert Path(db_path).exists()
        conn = get_connection("test-users")
        cur = conn.execute("SELECT name FROM users WHERE id = 1")
        assert cur.fetchone()[0] == "Alice"
        conn.close()
        stop_sqlite_mock("test-users")
        assert not Path(db_path).exists()


class TestProcess:
    """PID tracking and process management."""

    def test_write_and_read_pid(self):
        write_pid("test-svc", 12345)
        assert read_pid("test-svc") == 12345
        # cleanup
        (PID_DIR / "efm-test-svc.pid").unlink(missing_ok=True)

    def test_is_running_false(self):
        # PID 0 is always the scheduler — use a very high unlikely PID
        assert not is_running(999999)

    def test_stop_all_and_list_running(self):
        # Create a fake PID file pointing to a non-existent process
        write_pid("fake-http", 999998)
        write_pid("fake-db", 999997)
        # list_running should not show them because they are not alive
        running = list_running()
        names = [r["name"] for r in running]
        assert "fake-http" not in names
        assert "fake-db" not in names
        # cleanup
        (PID_DIR / "efm-fake-http.pid").unlink(missing_ok=True)
        (PID_DIR / "efm-fake-db.pid").unlink(missing_ok=True)
