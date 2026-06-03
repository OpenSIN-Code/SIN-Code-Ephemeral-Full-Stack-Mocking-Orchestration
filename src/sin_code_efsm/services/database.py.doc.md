# services/database.py

In-memory SQLite mock database.

## What it does

Wraps a `sqlite3.Connection` (`:memory:`) with thread-safe
helpers for DDL + DML. Mounts two FastAPI routes under `/db`:

- `POST /db/execute` — run any SQL, return rows as dicts
- `GET  /db/tables`  — list table names

Schemas registered via `create_table(ddl)` are re-applied on every
`reset()`, so a single test can run repeatedly against a clean DB
without losing the table structure.

## Dependencies

- `sqlite3`, `threading` (stdlib)
- `fastapi`

## Public API

| Symbol | Purpose |
|--------|---------|
| `DatabaseService` | The service class (`name="database"`, `prefix="/db"`) |
| `DatabaseService.create_table(ddl)` | Apply DDL, remember it for re-application |
| `DatabaseService.execute(sql, params)` | Run any SQL, return rows as dicts |
| `DatabaseService.executemany(sql, seq)` | Bulk insert/update |
| `DatabaseService.tables()` | List table names |
| `DatabaseService.reset()` | Wipe data, re-apply schemas |
| `DatabaseService.hard_reset()` | Wipe data AND drop schemas |

## Concurrency

- The connection is created with `check_same_thread=False` so the
  FastAPI gateway (in its own thread) and the test thread can share it.
- All access is serialized through `self._lock` (`threading.RLock`).

## Usage

```python
from sin_code_efsm.services.database import DatabaseService
db = DatabaseService()
db.create_table("CREATE TABLE users (id INTEGER, name TEXT)")
db.execute("INSERT INTO users VALUES (?, ?)", (1, "ada"))
print(db.execute("SELECT * FROM users"))
```

## Known caveats

- The DB is in-memory and dies with the process. There is no
  persistence layer.
- `reset()` re-applies schemas in registration order; do not
  assume a particular order if schemas reference each other.
- `executemany` returns `cur.rowcount` which can be `None` on
  older SQLite builds; callers should not rely on it.
