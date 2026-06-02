"""Mock OAuth2 / JWT authentication service.

Docs: auth.doc.md
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


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    rem = len(s) % 4
    if rem:
        s = s + ("=" * (4 - rem))
    return base64.urlsafe_b64decode(s.encode("ascii"))


class InvalidTokenError(Exception):
    """Raised when JWT validation fails (signature, format, or expiry)."""


class AuthService(BaseService):
    """Mock OAuth2 provider with HS256 JWT issuance and validation.

    The implementation is intentionally minimal — it is *not* a real auth
    server. It exists so code under test can hit ``/auth/oauth/token`` and get
    back a structurally valid JWT, and can call ``/auth/oauth/userinfo`` with a
    bearer token to confirm validation works.
    """

    name = "auth"
    prefix = "/auth"

    def __init__(self, secret: str | None = None, ttl_seconds: int = 3600) -> None:
        super().__init__()
        # Random per-instance secret so tests can't leak signatures.
        self._secret = secret or secrets.token_urlsafe(32)
        self._ttl = ttl_seconds
        self._lock = threading.RLock()
        self._users = StateStore()
        self._issued: list[str] = []

    # ── User registry (so userinfo can lie consistently) ───────────────

    def add_user(self, username: str, **claims: Any) -> dict[str, Any]:
        record = {"username": username, **claims}
        self._users.set(username, record)
        return record

    def get_user(self, username: str) -> dict[str, Any] | None:
        return self._users.get(username)

    # ── JWT operations ─────────────────────────────────────────────────

    def issue_jwt(
        self,
        subject: str = "user",
        extra: dict[str, Any] | None = None,
        ttl: int | None = None,
    ) -> str:
        """Generate and sign a JWT for ``subject``."""
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(time.time())
        payload: dict[str, Any] = {
            "sub": subject,
            "iat": now,
            "exp": now + (ttl if ttl is not None else self._ttl),
            "iss": "sin-code-efsm",
        }
        if extra:
            payload.update(extra)
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
        """Validate signature and expiry, return the payload."""
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
        with self._lock:
            return list(self._issued)

    # ── BaseService lifecycle ──────────────────────────────────────────

    def register_routes(self, app: FastAPI) -> None:
        @app.post(f"{self.prefix}/oauth/token")
        async def _token(request: Request):
            try:
                payload = await request.json()
            except Exception:
                payload = {}
            # Accept both ``form-ish`` and JSON bodies casually.
            username = (
                payload.get("username")
                or payload.get("client_id")
                or "anonymous"
            )
            grant_type = payload.get("grant_type", "password")
            token = self.issue_jwt(
                subject=username,
                extra={"grant_type": grant_type},
            )
            return {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": self._ttl,
                "scope": payload.get("scope", "read"),
            }

        @app.get(f"{self.prefix}/oauth/userinfo")
        async def _userinfo(authorization: str | None = Header(default=None)):
            if not authorization or not authorization.lower().startswith("bearer "):
                return JSONResponse(
                    {"error": "missing bearer token"}, status_code=401
                )
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
                return {"active": False}

    def reset(self) -> None:
        with self._lock:
            self._users.reset()
            self._issued.clear()
