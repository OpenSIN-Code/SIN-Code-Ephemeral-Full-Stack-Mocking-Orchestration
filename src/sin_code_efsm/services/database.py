"""In-memory SQLite mock database service.

Docs: services/database.py.doc.md
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

    Uses `check_same_thread=False` so the FastAPI gateway (running in its
    own thread) and the test thread can both use the same connection.
    Access is serialized through `self._lock` to keep that safe.

    All schema and data live in RAM. `reset()` rebuilds an empty
    connection, so a single test never sees data from a previous test.
    """

    name = "database"
    prefix = "/db"

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None
        self._schemas: list[str] = []
        # Open the in-memory connection eagerly so the very first
        # request doesn't pay the connection cost.
        self._open()

    # ── Connection management ──────────────────────────────────────────

    def _open(self) -> None:
        """Open a fresh in-memory connection (called from `__init__` and `reset`)."""
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        # `Row` factory makes rows indexable by column name, which is
        # what `execute()` relies on to build its dict output.
        self._conn.row_factory = sqlite3.Row

    def _close(self) -> None:
        """Close the connection if open; swallow errors to stay idempotent."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                # Closing twice is a no-op in modern sqlite3 but can
                # raise on some builds; we don't care.
                pass
            self._conn = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the live connection, opening it on demand if needed.

        Always call this instead of touching `self._conn` directly —
        it guarantees the connection is open under the lock.
        """
        with self._lock:
            if self._conn is None:
                self._open()
            assert self._conn is not None
            return self._conn

    # ── DDL / DML helpers ──────────────────────────────────────────────

    def create_table(self, ddl: str) -> None:
        """Execute a `CREATE TABLE` statement. Re-applied on `reset()`.

        The DDL string is stored in `self._schemas` so a subsequent
        `reset()` can rebuild the same schema.
        """
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
            # `cur.description` is `None` for statements that don't
            # produce rows (INSERT / UPDATE / DELETE). Returning `[]`
            # in that case lets the API return a stable shape.
            if cur.description is None:
                return []
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def executemany(self, sql: str, seq: list[tuple | list | dict]) -> int:
        """Run the same SQL against a sequence of parameter sets. Returns rowcount."""
        with self._lock:
            cur = self.connection.cursor()
            cur.executemany(sql, seq)
            self.connection.commit()
            return cur.rowcount

    def tables(self) -> list[str]:
        """List table names in the in-memory schema (alphabetical)."""
        rows = self.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [r["name"] for r in rows]

    # ── BaseService lifecycle ──────────────────────────────────────────

    def register_routes(self, app: FastAPI) -> None:
        """Mount `/db/execute` and `/db/tables` on the shared gateway."""
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
        """Wipe all rows but keep the registered schema."""
        with self._lock:
            self._close()
            self._open()
            # Re-apply registered schemas so structure survives reset.
            # A failed `execute` is silently swallowed: a stale schema
            # from a previous test is the caller's bug, not ours.
            for ddl in self._schemas:
                try:
                    self.connection.execute(ddl)
                except sqlite3.Error:
                    pass
            self.connection.commit()

    def hard_reset(self) -> None:
        """Drop everything, including the registered schema."""
        with self._lock:
            # Forget all schemas so a subsequent `reset()` starts
            # from a truly empty database.
            self._schemas.clear()
            self._close()
            self._open()
