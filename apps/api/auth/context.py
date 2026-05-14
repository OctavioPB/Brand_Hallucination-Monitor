"""OrgContext — authenticated organization context injected into every request.

Resolution order:
  1. X-API-Key header → ApiKeyORM lookup (server-to-server)
  2. Authorization: Bearer <jwt> → JWT decode

Both paths populate OrgContext with organization_id and role.
Rate limiting (100 req/min per org) is enforced here.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.jwt import decode_jwt
from apps.api.database import get_db
from apps.api.models.api_key import ApiKeyORM

logger = structlog.get_logger(__name__)

_API_KEY_HEADER = "X-API-Key"
_RATE_LIMIT_PER_MINUTE = 100
_RATE_WINDOW_SECONDS = 60

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class OrgContext:
    organization_id: str
    user_id: str
    role: str  # admin | analyst | viewer


async def get_org_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrgContext:
    """FastAPI dependency that resolves an OrgContext from the incoming request.

    Raises HTTP 401 if neither an API key nor a valid JWT is present.
    Raises HTTP 429 if the organization exceeds 100 requests/minute (Redis-backed).
    """
    org_ctx = await _resolve_auth(request, credentials, db)
    await _check_rate_limit(request, org_ctx)
    return org_ctx


async def _resolve_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> OrgContext:
    api_key_raw = request.headers.get(_API_KEY_HEADER)

    if api_key_raw:
        return await _auth_via_api_key(api_key_raw, db)

    if credentials and credentials.scheme.lower() == "bearer":
        return _auth_via_jwt(credentials.credentials)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: provide X-API-Key header or Authorization: Bearer token",
    )


async def _auth_via_api_key(raw_key: str, db: AsyncSession) -> OrgContext:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    result = await db.execute(
        select(ApiKeyORM).where(ApiKeyORM.key_hash == key_hash, ApiKeyORM.is_active == True)  # noqa: E712
    )
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if api_key.expires_at is not None:
        from datetime import datetime, timezone
        if api_key.expires_at < datetime.now(tz=timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    # Update last_used_at non-blocking (best-effort)
    try:
        from datetime import datetime, timezone
        await db.execute(
            update(ApiKeyORM)
            .where(ApiKeyORM.id == api_key.id)
            .values(last_used_at=datetime.now(tz=timezone.utc))
        )
        await db.flush()
    except Exception:
        pass

    return OrgContext(
        organization_id=api_key.organization_id,
        user_id=f"apikey:{api_key.id}",
        role=api_key.role,
    )


def _auth_via_jwt(token: str) -> OrgContext:
    payload = decode_jwt(token)

    # Support flat payload and Supabase app_metadata nesting
    app_meta = payload.get("app_metadata", {}) or {}
    organization_id = payload.get("organization_id") or app_meta.get("organization_id", "")
    role = payload.get("role") or app_meta.get("role", "viewer")
    user_id = payload.get("sub", "")

    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT missing organization_id claim",
        )

    return OrgContext(organization_id=organization_id, user_id=user_id, role=role)


async def _check_rate_limit(request: Request, org_ctx: OrgContext) -> None:
    """Token bucket: 100 requests/60s per organization_id.

    Uses Redis if available; fails open if Redis is unreachable (fail-open policy
    is acceptable for rate limiting — a brief Redis outage shouldn't break the API).
    """
    try:
        import redis.asyncio as aioredis
        from apps.api.config import get_settings

        settings = get_settings()
        r = aioredis.from_url(settings.redis_url, decode_responses=True)

        bucket_key = f"rl:{org_ctx.organization_id}"
        now_window = int(time.time()) // _RATE_WINDOW_SECONDS
        key = f"{bucket_key}:{now_window}"

        count = await r.incr(key)
        if count == 1:
            await r.expire(key, _RATE_WINDOW_SECONDS * 2)

        await r.aclose()

        if count > _RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {_RATE_LIMIT_PER_MINUTE} requests/minute",
                headers={"Retry-After": str(_RATE_WINDOW_SECONDS)},
            )

    except HTTPException:
        raise
    except Exception:
        # Fail open — Redis unavailability must not break the API
        logger.warning("Rate limit check failed, skipping", org_id=org_ctx.organization_id)


# Re-export OrgContextDep as a convenient type alias for router signatures
OrgContextDep = Annotated[OrgContext, Depends(get_org_context)]
