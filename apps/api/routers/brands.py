"""Brand management endpoints — CRUD + manifest updates."""
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.models.brand import Brand, BrandManifest, BrandORM

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/brands", tags=["brands"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# GET /api/v1/brands/{brand_id}
# ---------------------------------------------------------------------------

@router.get("/{brand_id}", response_model=Brand)
async def get_brand(brand_id: uuid.UUID, db: DbDep) -> Brand:
    """Return a single brand by ID."""
    result = await db.execute(select(BrandORM).where(BrandORM.id == brand_id))
    orm = result.scalar_one_or_none()
    if orm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return Brand.model_validate(orm)


# ---------------------------------------------------------------------------
# PUT /api/v1/brands/{brand_id}/manifest
# ---------------------------------------------------------------------------

@router.put("/{brand_id}/manifest", response_model=Brand)
async def update_brand_manifest(
    brand_id: uuid.UUID,
    manifest: BrandManifest,
    db: DbDep,
) -> Brand:
    """Replace the ground-truth manifest for a brand.

    The manifest drives hallucination detection:
    - true_attributes: what the brand actually is
    - false_attributes: claims that are factually wrong
    - competitor_list: brands that should not be positively confused with this one
    - regulatory_claims_to_avoid: phrases that must never appear in LLM responses
    """
    result = await db.execute(select(BrandORM).where(BrandORM.id == brand_id))
    orm = result.scalar_one_or_none()
    if orm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")

    orm.manifest = manifest.model_dump()
    await db.commit()
    await db.refresh(orm)

    logger.info(
        "Brand manifest updated",
        brand_id=str(brand_id),
        true_attributes=len(manifest.true_attributes),
        false_attributes=len(manifest.false_attributes),
        regulatory_claims=len(manifest.regulatory_claims_to_avoid),
    )

    return Brand.model_validate(orm)
