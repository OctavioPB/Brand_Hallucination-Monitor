"""JWT validation for hallucin8.

Supports HS256 tokens (used for both internal dev tokens and Supabase
projects configured with the project JWT secret).

Usage:
  payload = decode_jwt(token)
  organization_id = payload.get("organization_id")

Token generation for tests / dev:
  from apps.api.auth.jwt import create_token
  token = create_token(organization_id="org-123", role="admin")
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from fastapi import HTTPException, status

logger = structlog.get_logger(__name__)


def _get_secret() -> str:
    from apps.api.config import get_settings
    return get_settings().jwt_secret


def decode_jwt(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Raises HTTP 401 on any validation failure."""
    try:
        import jwt as pyjwt
    except ImportError as exc:
        raise RuntimeError("PyJWT not installed — add 'PyJWT>=2.8.0' to dependencies") from exc

    try:
        payload: dict[str, Any] = pyjwt.decode(
            token,
            _get_secret(),
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except pyjwt.InvalidTokenError as exc:
        logger.warning("JWT validation failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or malformed token"
        )


def create_token(
    organization_id: str,
    user_id: str = "test-user",
    role: str = "admin",
    expires_in: timedelta = timedelta(hours=24),
) -> str:
    """Create a signed HS256 JWT — for tests and local dev only."""
    try:
        import jwt as pyjwt
    except ImportError as exc:
        raise RuntimeError("PyJWT not installed") from exc

    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user_id,
        "organization_id": organization_id,
        "role": role,
        "iat": now,
        "exp": now + expires_in,
    }
    return pyjwt.encode(payload, _get_secret(), algorithm="HS256")
