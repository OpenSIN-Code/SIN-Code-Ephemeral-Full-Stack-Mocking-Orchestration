# `auth.py` — Auth Mock Service

What this file does: mock OAuth2 / JWT issuance and validation (HS256, no external dependencies).

## Dependencies

- Imported by: `server.py`, tests
- Imports: `base` (BaseService)

## Public API

- `AuthService(prefix="/auth")` — mock auth service
- `issue_token(sub, scopes)` — create a JWT
- `validate_token(token)` — verify a JWT and return claims

## Usage

```python
from sin_code_efsm.services.auth import AuthService
auth = AuthService()
token = auth.issue_token("user-123", ["read", "write"])
```

## Notes

Uses a hardcoded secret for testing. Do NOT use in production.
