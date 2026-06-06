"""SQLite in-memory mock database from YAML config.

Runs in the CLI process (no background server needed) because an in-memory
DB is private to the process that creates it. For tests, a ``:memory:``
connection is opened; for sharing, a file-based DB on ``/tmp`` is used.

Docs: db_mock.doc.md
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def start_sqlite_mock(name: str, schema: str, seed: list[str] | None = None) -> str:
    """Create a SQLite DB and return its connection URI.

    Uses a file under ``/tmp`` so the DB persists across the CLI process
    and can be inspected by external tools. For true ephemeral tests,
    ``:memory:`` is an option, but it disappears when the CLI exits.
    """
    db_path = f"/tmp/efm-{name}.db"
    conn = sqlite3.connect(db_path)
    try:
        if schema:
            conn.executescript(schema)
        for stmt in seed or []:
            if stmt.strip():
                conn.execute(stmt)
        conn.commit()
    finally:
        conn.close()
    return db_path


def get_connection(name: str) -> sqlite3.Connection:
    """Open a connection to a previously-started mock DB."""
    db_path = f"/tmp/efm-{name}.db"
    return sqlite3.connect(db_path)


def stop_sqlite_mock(name: str) -> None:
    """Remove the on-disk DB file."""
    db_path = Path(f"/tmp/efm-{name}.db")
    db_path.unlink(missing_ok=True)
