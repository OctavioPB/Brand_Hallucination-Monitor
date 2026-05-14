"""Auth endpoints — API key management."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.api_keys import create_api_key, require_role
from apps.api.auth.context import OrgContextDep
from apps.api.database import get_db
from apps.api.models.api_key import ApiKeyORM

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    role: str = Field(default="analyst", pattern="^(admin|analyst|viewer)$")
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    organization_id: str
    name: str
    role: str
    is_active: bool
    created_at: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None


class ApiKeyCreated(ApiKeyResponse):
    """Only returned once on creation — contains the raw key."""
    raw_key: str


# ---------------------------------------------------------------------------
# POST /api/v1/auth/api-keys
# ---------------------------------------------------------------------------

@router.post(
    "/api-keys",
    response_model=ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_role("admin")],
)
async def create_new_api_key(
    payload: ApiKeyCreate,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> ApiKeyCreated:
    """Create a new API key. The raw key is returned once and cannot be recovered."""
    api_key_orm, raw_key = await create_api_key(
        db,
        organization_id=org_ctx.organization_id,
        name=payload.name,
        role=payload.role,
        expires_at=payload.expires_at,
    )
    await db.commit()
    await db.refresh(api_key_orm)

    logger.info(
        "API key created",
        org_id=org_ctx.organization_id,
        key_id=str(api_key_orm.id),
        role=payload.role,
    )

    response = ApiKeyResponse.model_validate(api_key_orm)
    return ApiKeyCreated(**response.model_dump(), raw_key=raw_key)


# ---------------------------------------------------------------------------
# GET /api/v1/auth/api-keys
# ---------------------------------------------------------------------------

@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(org_ctx: OrgContextDep, db: DbDep) -> list[ApiKeyResponse]:
    """List all API keys for the caller's organization (raw key is never returned)."""
    result = await db.execute(
        select(ApiKeyORM).where(ApiKeyORM.organization_id == org_ctx.organization_id)
        .order_by(ApiKeyORM.created_at.desc())
    )
    keys = result.scalars().all()
    return [ApiKeyResponse.model_validate(k) for k in keys]


# ---------------------------------------------------------------------------
# DELETE /api/v1/auth/api-keys/{key_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_role("admin")],
)
async def revoke_api_key(
    key_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> None:
    """Revoke (deactivate) an API key. Org isolation: can only revoke own org's keys."""
    result = await db.execute(
        select(ApiKeyORM).where(
            ApiKeyORM.id == key_id,
            ApiKeyORM.organization_id == org_ctx.organization_id,
        )
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    api_key.is_active = False
    await db.commit()
