"""Mock OAuth2 / JWT authentication service.

Docs: auth.py.doc.md
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from ..state import StateStore
from .base import BaseService


# ── Minimal HS256 JWT (no external deps) ───────────────────────────────


# Standard base64url padding: encoded output drops `=`; the decoder
# must add the right number back before calling `urlsafe_b64decode`.
_B64_PAD_CHAR = "="


def _b64url_encode(data: bytes) -> str:
    """Base64url-encode `data` with padding stripped (JWT convention)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Inverse of `_b64url_encode`: restore padding then decode."""
    rem = len(s) % 4
    if rem:
        s = s + (_B64_PAD_CHAR * (4 - rem))
    return base64.urlsafe_b64decode(s.encode("ascii"))


class InvalidTokenError(Exception):
    """Raised when JWT validation fails (signature, format, or expiry)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# Default token lifetime: 1 hour. The OAuth2 spec doesn't pin a
# value; 1h is a reasonable default for test purposes.
_DEFAULT_TTL_SECONDS = 3600

# Default JWT issuer claim. Used to identify tokens minted by this
# mock so they can be distinguished from real OAuth2 tokens in
# production logs.
_ISSUER = "sin-code-efsm"

# Supported OAuth2 grant types we accept on `/oauth/token`.
_DEFAULT_GRANT_TYPE = "password"
_DEFAULT_SCOPE = "read"
_DEFAULT_USERNAME = "anonymous"


class AuthService(BaseService):
    """Mock OAuth2 provider with HS256 JWT issuance and validation.

    The implementation is intentionally minimal — it is *not* a real auth
    server. It exists so code under test can hit `/auth/oauth/token` and
    get back a structurally valid JWT, and can call `/auth/oauth/userinfo`
    with a bearer token to confirm validation works.
    """

    name = "auth"
    prefix = "/auth"

    def __init__(self, secret: str | None = None, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
        super().__init__()
        # Random per-instance secret so tests can't leak signatures
        # across instances (e.g. when one process imports another).
        self._secret = secret or secrets.token_urlsafe(32)
        self._ttl = ttl_seconds
        # `RLock` because `validate_jwt` is called from request
        # handlers that may themselves take the lock elsewhere.
        self._lock = threading.RLock()
        self._users = StateStore()
        self._issued: list[str] = []

    # ── User registry (so userinfo can lie consistently) ───────────────

    def add_user(self, username: str, **claims: Any) -> dict[str, Any]:
        """Register a user record; later retrievable via `get_user`."""
        record = {"username": username, **claims}
        self._users.set(username, record)
        return record

    def get_user(self, username: str) -> dict[str, Any] | None:
        """Fetch a registered user (or `None` if not registered)."""
        return self._users.get(username)

    # ── JWT operations ─────────────────────────────────────────────────

    def issue_jwt(
        self,
        subject: str = "user",
        extra: dict[str, Any] | None = None,
        ttl: int | None = None,
    ) -> str:
        """Generate and sign a JWT for `subject`.

        Args:
            subject: Value for the `sub` claim (typically a user id).
            extra: Optional additional claims merged into the payload.
            ttl: Override the per-instance TTL for this one token.

        Returns:
            The signed JWT (`header.payload.signature`).
        """
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": subject,
            "iat": now,
            # `ttl or self._ttl` is wrong: `ttl=0` would fall back
            # to the default. The explicit `is not None` check is
            # what makes "0 seconds to live" actually work.
            "exp": now + (ttl if ttl is not None else self._ttl),
            "iss": _ISSUER,
        }
        if extra:
            payload.update(extra)
        # `separators=(",", ":")` strips spaces; `sort_keys=True`
        # makes the signature deterministic (header + payload are
        # signed as bytes — any whitespace difference would change
        # the signature).
        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
        payload_b64 = _b64url_encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        )
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig = hmac.new(
            self._secret.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        token = f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}"
        with self._lock:
            self._issued.append(token)
        return token

    def validate_jwt(self, token: str) -> dict[str, Any]:
        """Validate signature and expiry; return the payload.

        Args:
            token: The JWT string.

        Returns:
            The decoded payload dict.

        Raises:
            InvalidTokenError: On any failure (format, signature,
                payload parse, or expiry).
        """
        if not isinstance(token, str) or token.count(".") != 2:
            raise InvalidTokenError("invalid JWT format")
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected = hmac.new(
            self._secret.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        try:
            actual = _b64url_decode(sig_b64)
        except Exception as exc:
            raise InvalidTokenError("malformed signature") from exc
        # `hmac.compare_digest` is constant-time — important for
        # auth code that an attacker can't time-attack the signature.
        if not hmac.compare_digest(expected, actual):
            raise InvalidTokenError("signature mismatch")
        try:
            payload = json.loads(_b64url_decode(payload_b64))
        except Exception as exc:
            raise InvalidTokenError("malformed payload") from exc
        exp = payload.get("exp")
        if exp is not None and int(exp) < int(time.time()):
            raise InvalidTokenError("token expired")
        return payload

    @property
    def issued_tokens(self) -> list[str]:
        """Snapshot of every token this instance has signed (test-only helper)."""
        with self._lock:
            return list(self._issued)

    # ── BaseService lifecycle ──────────────────────────────────────────

    def register_routes(self, app: FastAPI) -> None:
        """Mount `/auth/oauth/{token,userinfo,introspect}` on the gateway."""
        @app.post(f"{self.prefix}/oauth/token")
        async def _token(request: Request):
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            # Accept both form-ish and JSON bodies casually so a
            # caller's existing OAuth2 client works without changes.
            username = (
                payload.get("username")
                or payload.get("client_id")
                or _DEFAULT_USERNAME
            )
            grant_type = payload.get("grant_type", _DEFAULT_GRANT_TYPE)
            token = self.issue_jwt(
                subject=username,
                extra={"grant_type": grant_type},
            )
            return {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": self._ttl,
                "scope": payload.get("scope", _DEFAULT_SCOPE),
            }

        @app.get(f"{self.prefix}/oauth/userinfo")
        async def _userinfo(authorization: str | None = Header(default=None)):
            if not authorization or not authorization.lower().startswith("bearer "):
                return JSONResponse(
                    {"error": "missing bearer token"}, status_code=401
                )
            # `split(" ", 1)[1]` so a token with spaces in the
            # value (rare but legal per RFC 6750) is preserved.
            token = authorization.split(" ", 1)[1].strip()
            try:
                claims = self.validate_jwt(token)
            except InvalidTokenError as exc:
                return JSONResponse({"error": str(exc)}, status_code=401)
            user = self.get_user(claims.get("sub", "")) or {}
            return {"claims": claims, "user": user}

        @app.post(f"{self.prefix}/oauth/introspect")
        async def _introspect(request: Request):
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            token = payload.get("token", "")
            try:
                claims = self.validate_jwt(token)
                return {"active": True, **claims}
            except InvalidTokenError:
                # Per RFC 7662: invalid tokens return `active: false`
                # with no error detail (don't leak why it failed).
                return {"active": False}

    def reset(self) -> None:
        """Clear the user registry and the issued-token log."""
        with self._lock:
            self._users.reset()
            self._issued.clear()
