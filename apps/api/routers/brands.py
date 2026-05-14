"""Brand management endpoints — CRUD + manifest + SPS + hallucinations."""
from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.context import OrgContextDep
from apps.api.database import get_db
from apps.api.models.brand import Brand, BrandCreate, BrandManifest, BrandORM
from apps.api.models.probe_result import ProbeResultORM
from apps.api.models.sps_score import SPSScore, SPSScoreORM

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/brands", tags=["brands"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class HallucinationSummary(BaseModel):
    """Summary row returned by GET /{id}/hallucinations — read from probe_results."""
    probe_id: uuid.UUID
    model_name: str
    probe_prompt: str
    llm_response: str
    hallucinations_detected: int
    cost_usd: float
    dag_run_id: str
    probed_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_brand_or_404(
    brand_id: uuid.UUID, org_ctx: OrgContextDep, db: AsyncSession
) -> BrandORM:
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
# GET /api/v1/brands
# ---------------------------------------------------------------------------

@router.get("", response_model=list[Brand])
async def list_brands(org_ctx: OrgContextDep, db: DbDep) -> list[Brand]:
    """List all brands belonging to the caller's organization."""
    result = await db.execute(
        select(BrandORM)
        .where(BrandORM.organization_id == org_ctx.organization_id)
        .order_by(BrandORM.name)
    )
    return [Brand.model_validate(b) for b in result.scalars().all()]


# ---------------------------------------------------------------------------
# POST /api/v1/brands
# ---------------------------------------------------------------------------

@router.post("", response_model=Brand, status_code=status.HTTP_201_CREATED)
async def create_brand(
    payload: BrandCreate,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> Brand:
    """Create a new brand under the caller's organization."""
    # Slug uniqueness is enforced by DB unique constraint; surface it as 409
    existing = await db.execute(select(BrandORM).where(BrandORM.slug == payload.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Brand slug '{payload.slug}' already exists",
        )

    brand = BrandORM(
        id=uuid.uuid4(),
        organization_id=org_ctx.organization_id,
        name=payload.name,
        slug=payload.slug,
        manifest=payload.manifest.model_dump() if payload.manifest else None,
    )
    db.add(brand)
    await db.commit()
    await db.refresh(brand)

    logger.info("Brand created", brand_id=str(brand.id), slug=brand.slug, org_id=org_ctx.organization_id)
    return Brand.model_validate(brand)


# ---------------------------------------------------------------------------
# GET /api/v1/brands/{brand_id}
# ---------------------------------------------------------------------------

@router.get("/{brand_id}", response_model=Brand)
async def get_brand(brand_id: uuid.UUID, org_ctx: OrgContextDep, db: DbDep) -> Brand:
    """Return a single brand by ID (org-isolated)."""
    return Brand.model_validate(await _get_brand_or_404(brand_id, org_ctx, db))


# ---------------------------------------------------------------------------
# PUT /api/v1/brands/{brand_id}/manifest
# ---------------------------------------------------------------------------

@router.put("/{brand_id}/manifest", response_model=Brand)
async def update_brand_manifest(
    brand_id: uuid.UUID,
    manifest: BrandManifest,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> Brand:
    """Replace the ground-truth manifest for a brand.

    The manifest drives hallucination detection:
    - true_attributes: what the brand actually is
    - false_attributes: claims that are factually wrong
    - competitor_list: brands that should not be positively confused
    - regulatory_claims_to_avoid: phrases that must never appear in LLM responses
    """
    orm = await _get_brand_or_404(brand_id, org_ctx, db)
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


# ---------------------------------------------------------------------------
# GET /api/v1/brands/{brand_id}/sps
# ---------------------------------------------------------------------------

@router.get("/{brand_id}/sps", response_model=list[SPSScore])
async def get_sps_scores(
    brand_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
    cluster: str | None = Query(default=None, description="Filter by intent_cluster_slug"),
    limit: int = Query(default=100, le=500),
) -> list[SPSScore]:
    """Time-series SPS scores for a brand, ordered by calculated_at desc."""
    await _get_brand_or_404(brand_id, org_ctx, db)

    query = (
        select(SPSScoreORM)
        .where(SPSScoreORM.brand_id == brand_id)
        .order_by(SPSScoreORM.calculated_at.desc())
        .limit(limit)
    )
    if cluster:
        query = query.where(SPSScoreORM.intent_cluster_slug == cluster)

    result = await db.execute(query)
    return [SPSScore.model_validate(s) for s in result.scalars().all()]


# ---------------------------------------------------------------------------
# GET /api/v1/brands/{brand_id}/hallucinations
# ---------------------------------------------------------------------------

@router.get("/{brand_id}/hallucinations", response_model=list[HallucinationSummary])
async def get_hallucination_history(
    brand_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
    only_detected: bool = Query(default=False, description="Return only probes with ≥1 hallucination"),
    limit: int = Query(default=50, le=200),
) -> list[HallucinationSummary]:
    """Probe results with hallucination counts for a brand (from probe_results table)."""
    await _get_brand_or_404(brand_id, org_ctx, db)

    query = (
        select(ProbeResultORM)
        .where(
            ProbeResultORM.brand_id == brand_id,
            ProbeResultORM.organization_id == org_ctx.organization_id,
        )
        .order_by(ProbeResultORM.probed_at.desc())
        .limit(limit)
    )
    if only_detected:
        query = query.where(ProbeResultORM.hallucinations_detected > 0)

    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        HallucinationSummary(
            probe_id=r.id,
            model_name=r.model_name,
            probe_prompt=r.probe_prompt,
            llm_response=r.llm_response,
            hallucinations_detected=r.hallucinations_detected,
            cost_usd=float(r.cost_usd),
            dag_run_id=r.dag_run_id,
            probed_at=r.probed_at.isoformat(),
        )
        for r in rows
    ]
