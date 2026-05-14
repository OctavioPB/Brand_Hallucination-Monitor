"""Competitor management endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.context import OrgContextDep
from apps.api.database import get_db
from apps.api.models.brand import BrandORM
from apps.api.models.competitor import Competitor, CompetitorCreate, CompetitorORM

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/brands", tags=["competitors"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _get_brand_or_404(
    brand_id: uuid.UUID, org_ctx: OrgContextDep, db: AsyncSession
) -> BrandORM:
    """Load a brand, enforcing org isolation."""
    result = await db.execute(
        select(BrandORM).where(
            BrandORM.id == brand_id,
            BrandORM.organization_id == org_ctx.organization_id,
        )
    )
    brand = result.scalar_one_or_none()
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return brand


# ---------------------------------------------------------------------------
# GET /api/v1/brands/{brand_id}/competitors
# ---------------------------------------------------------------------------

@router.get("/{brand_id}/competitors", response_model=list[Competitor])
async def list_competitors(
    brand_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> list[Competitor]:
    """List all tracked competitors for a brand."""
    await _get_brand_or_404(brand_id, org_ctx, db)

    result = await db.execute(
        select(CompetitorORM)
        .where(CompetitorORM.brand_id == brand_id)
        .order_by(CompetitorORM.competitor_name)
    )
    return [Competitor.model_validate(c) for c in result.scalars().all()]


# ---------------------------------------------------------------------------
# POST /api/v1/brands/{brand_id}/competitors
# ---------------------------------------------------------------------------

@router.post(
    "/{brand_id}/competitors",
    response_model=Competitor,
    status_code=status.HTTP_201_CREATED,
)
async def add_competitor(
    brand_id: uuid.UUID,
    payload: CompetitorCreate,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> Competitor:
    """Add a competitor to monitor for a brand."""
    await _get_brand_or_404(brand_id, org_ctx, db)

    competitor = CompetitorORM(
        id=uuid.uuid4(),
        brand_id=brand_id,
        competitor_name=payload.competitor_name,
        competitor_slug=payload.competitor_slug,
    )
    db.add(competitor)
    await db.commit()
    await db.refresh(competitor)

    logger.info(
        "Competitor added",
        brand_id=str(brand_id),
        competitor=payload.competitor_name,
        org_id=org_ctx.organization_id,
    )
    return Competitor.model_validate(competitor)


# ---------------------------------------------------------------------------
# DELETE /api/v1/brands/{brand_id}/competitors/{competitor_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{brand_id}/competitors/{competitor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_competitor(
    brand_id: uuid.UUID,
    competitor_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> None:
    """Remove a competitor from monitoring."""
    await _get_brand_or_404(brand_id, org_ctx, db)

    result = await db.execute(
        select(CompetitorORM).where(
            CompetitorORM.id == competitor_id,
            CompetitorORM.brand_id == brand_id,
        )
    )
    competitor = result.scalar_one_or_none()
    if competitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")

    await db.delete(competitor)
    await db.commit()
