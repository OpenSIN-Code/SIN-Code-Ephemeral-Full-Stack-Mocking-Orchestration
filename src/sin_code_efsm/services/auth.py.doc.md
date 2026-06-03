# services/auth.py

Mock OAuth2 / JWT authentication service.

## What it does

A self-contained HS256 JWT issuer/validator with three FastAPI
endpoints:

- `POST /auth/oauth/token` — issues a token (accepts both JSON and
  form-ish bodies).
- `GET  /auth/oauth/userinfo` — validates a `Bearer` header, returns
  the JWT claims + the registered user record.
- `POST /auth/oauth/introspect` — RFC 7662-style introspection.

The implementation is intentionally minimal — it is NOT a real
auth server. It exists so code under test can get back a
structurally valid JWT and confirm validation works.

## Dependencies

- `base64`, `hmac`, `hashlib`, `json`, `secrets`, `time` (stdlib)
- `fastapi`
- `state.py` — `StateStore`

## Public API

| Symbol | Purpose |
|--------|---------|
| `InvalidTokenError` | Raised by `validate_jwt` on any failure |
| `AuthService` | The service class (`name="auth"`, `prefix="/auth"`) |
| `AuthService.add_user(username, **claims)` | Register a user |
| `AuthService.get_user(username)` | Fetch a registered user |
| `AuthService.issue_jwt(subject, extra, ttl)` | Sign a JWT |
| `AuthService.validate_jwt(token)` | Verify + return payload |
| `AuthService.issued_tokens` | List of tokens signed by this instance |

## Defaults

- `_ttl` (default 3600 s = 1 hour) — token lifetime.
- `_secret` — random per-instance if not supplied, so tests cannot
  leak signatures across runs.

## Usage

```python
from sin_code_efsm.services.auth import AuthService
auth = AuthService()
auth.add_user("ada", email="ada@example.com")
token = auth.issue_jwt(subject="ada")
claims = auth.validate_jwt(token)
```

## Known caveats

- HS256 only — no RS256 / EdDSA support.
- `validate_jwt` checks signature + `exp`. It does not check `iat`
  for future-dated tokens, `nbf`, or `aud`.
- The `_users` store is keyed by `username`; multiple registrations
  for the same username overwrite.
