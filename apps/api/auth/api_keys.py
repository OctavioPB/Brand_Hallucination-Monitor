"""API key generation and management utilities."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.context import OrgContextDep
from apps.api.models.api_key import ApiKeyORM


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key. Returns (raw_key, key_hash).

    The raw key is shown to the user ONCE and never stored.
    Only the SHA-256 hash is persisted.
    """
    raw = f"hk_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_hash


async def create_api_key(
    db: AsyncSession,
    organization_id: str,
    name: str,
    role: str = "analyst",
    expires_at: datetime | None = None,
) -> tuple[ApiKeyORM, str]:
    """Persist a new API key. Returns (ApiKeyORM, raw_key).

    The raw_key must be delivered to the caller — it cannot be recovered later.
    """
    raw_key, key_hash = generate_api_key()
    api_key = ApiKeyORM(
        id=uuid.uuid4(),
        organization_id=organization_id,
        name=name,
        key_hash=key_hash,
        role=role,
        is_active=True,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.flush()
    return api_key, raw_key


def require_role(*allowed_roles: str):
    """FastAPI dependency factory that enforces role-based access.

    Usage:
        @router.delete("/{id}", dependencies=[Depends(require_role("admin"))])
    """
    async def _check(org_ctx: OrgContextDep) -> None:
        if org_ctx.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{org_ctx.role}' is not authorized. Required: {allowed_roles}",
            )

    return Depends(_check)
