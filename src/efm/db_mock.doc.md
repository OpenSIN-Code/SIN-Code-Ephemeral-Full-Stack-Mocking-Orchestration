# `db_mock.py` — SQLite Mock

What: Creates a file-based SQLite database from a schema string and optional
seed INSERT statements.

Dependencies: `sqlite3` (stdlib)

Usage:
```python
from efm.db_mock import start_sqlite_mock, get_connection
path = start_sqlite_mock("mydb", "CREATE TABLE t (id INT);", ["INSERT INTO t VALUES (1);"])
conn = get_connection("mydb")
```

Caveats: Uses a file under `/tmp` so the DB persists after `efm up` returns.
`stop_sqlite_mock` removes the file.
