"""In-memory SQLite mock database service.

Docs: database.doc.md
"""
from __future__ import annotations

import sqlite3
import threading
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .base import BaseService


class DatabaseService(BaseService):
    """Ephemeral in-memory SQLite.

    Uses ``check_same_thread=False`` so the FastAPI gateway (running in its own
    thread) and the test thread can both use the same connection. Access is
    serialized through ``self._lock`` to keep that safe.

    All schema and data live in RAM. ``reset()`` rebuilds an empty connection,
    so a single test never sees data from a previous test.
    """

    name = "database"
    prefix = "/db"

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None
        self._schemas: list[str] = []
        self._open()

    # ── Connection management ──────────────────────────────────────────

    def _open(self) -> None:
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def _close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    @property
    def connection(self) -> sqlite3.Connection:
        with self._lock:
            if self._conn is None:
                self._open()
            assert self._conn is not None
            return self._conn

    # ── DDL / DML helpers ──────────────────────────────────────────────

    def create_table(self, ddl: str) -> None:
        """Execute a ``CREATE TABLE`` statement. Re-applied on ``reset()``."""
        with self._lock:
            self.connection.execute(ddl)
            self.connection.commit()
            self._schemas.append(ddl)

    def execute(self, sql: str, params: tuple | list | dict | None = None) -> list[dict[str, Any]]:
        """Run any SQL. Returns rows as dicts (empty list for non-SELECT)."""
        with self._lock:
            cur = self.connection.cursor()
            cur.execute(sql, params or ())
            self.connection.commit()
            if cur.description is None:
                return []
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def executemany(self, sql: str, seq: list[tuple | list | dict]) -> int:
        with self._lock:
            cur = self.connection.cursor()
            cur.executemany(sql, seq)
            self.connection.commit()
            return cur.rowcount

    def tables(self) -> list[str]:
        rows = self.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [r["name"] for r in rows]

    # ── BaseService lifecycle ──────────────────────────────────────────

    def register_routes(self, app: FastAPI) -> None:
        @app.post(f"{self.prefix}/execute")
        async def _execute(request: Request):
            payload = await request.json()
            sql = payload.get("sql", "")
            params = payload.get("params", [])
            if not sql:
                return JSONResponse({"error": "missing sql"}, status_code=400)
            try:
                rows = self.execute(sql, params)
                return {"rows": rows, "row_count": len(rows)}
            except sqlite3.Error as exc:
                return JSONResponse({"error": str(exc)}, status_code=400)

        @app.get(f"{self.prefix}/tables")
        async def _tables():
            return {"tables": self.tables()}

    def reset(self) -> None:
        with self._lock:
            self._close()
            self._open()
            # Re-apply registered schemas so structure survives reset.
            for ddl in self._schemas:
                try:
                    self.connection.execute(ddl)
                except sqlite3.Error:
                    pass
            self.connection.commit()

    def hard_reset(self) -> None:
        """Drop everything, including schema."""
        with self._lock:
            self._schemas.clear()
            self._close()
            self._open()
