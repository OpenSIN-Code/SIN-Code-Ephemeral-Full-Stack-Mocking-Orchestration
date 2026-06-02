# `database.py` — Database Mock Service

What this file does: in-memory SQLite with HTTP SQL execution and schema setup/teardown.

## Dependencies

- Imported by: `server.py`, tests
- Imports: `base` (BaseService)

## Public API

- `DatabaseService(prefix="/db")` — mock database service
- `execute(sql)` — run SQL and return results
- `setup_schema(ddl)` — apply DDL statements

## Usage

```python
from sin_code_efsm.services.database import DatabaseService
db = DatabaseService()
db.setup_schema("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);")
```

## Notes

All data is stored in `:memory:` SQLite and wiped on `reset()`.
