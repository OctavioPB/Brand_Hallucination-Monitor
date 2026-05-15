"""Internal admin panel API — org management, scan oversight, cost aggregation.

Protected by ADMIN_SECRET header (set via ADMIN_SECRET env var).
Not part of the per-org API key auth flow.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.models.embedding_cost import EmbeddingCostORM
from apps.api.models.onboarding import NpsResponseORM, OnboardingStateORM, OrganizationORM
from apps.api.models.scan_job import ScanJobORM

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

_ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change-me-admin-secret")


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

async def require_admin_secret(x_admin_secret: Annotated[str, Header()] = "") -> None:
    if x_admin_secret != _ADMIN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Admin-Secret header.",
        )


AdminDep = Depends(require_admin_secret)


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------

class OrgRow(BaseModel):
    org_id: str
    name: str
    email: str
    plan: str
    is_demo: bool
    onboarding_completed: bool
    created_at: datetime
    total_spend_usd: float
    brand_count: int
    scan_job_count: int


class ScanJobRow(BaseModel):
    job_id: str
    org_id: str
    brand_id: str
    job_type: str
    status: str
    created_at: datetime
    completed_at: datetime | None


class CostPerOrgRow(BaseModel):
    org_id: str
    total_spend_usd: float
    api_calls: int
    tokens_total: int


class NpsRow(BaseModel):
    org_id: str
    score: int
    comment: str | None
    trigger: str
    created_at: datetime


class AdminStatsResponse(BaseModel):
    total_orgs: int
    active_orgs_7d: int
    avg_nps: float | None
    p1_open_bugs: int  # placeholder — wired to GitHub when API key set


# ---------------------------------------------------------------------------
# GET /api/v1/admin/orgs
# ---------------------------------------------------------------------------

@router.get("/orgs", response_model=list[OrgRow], dependencies=[AdminDep])
async def list_orgs(
    db: DbDep,
    skip: int = 0,
    limit: int = 100,
    demo: bool | None = None,
) -> list[OrgRow]:
    """List all organizations with spend and activity summary."""
    q = select(OrganizationORM).order_by(OrganizationORM.created_at.desc()).offset(skip).limit(limit)
    if demo is not None:
        q = q.where(OrganizationORM.is_demo == demo)

    result = await db.execute(q)
    orgs = result.scalars().all()

    rows: list[OrgRow] = []
    for org in orgs:
        org_id = org.slug

        # Total spend (may be empty table in dev)
        spend_result = await db.execute(
            select(func.coalesce(func.sum(EmbeddingCostORM.cost_usd), 0)).where(
                EmbeddingCostORM.org_id == org_id
            )
        )
        total_spend = float(spend_result.scalar() or 0)

        # Scan job count (via brand join is expensive — use subquery approach)
        from apps.api.models.brand import BrandORM
        brand_ids_result = await db.execute(
            select(BrandORM.id).where(BrandORM.organization_id == org_id)
        )
        brand_ids = [r for r in brand_ids_result.scalars().all()]
        brand_count = len(brand_ids)

        scan_count = 0
        if brand_ids:
            scan_result = await db.execute(
                select(func.count()).where(ScanJobORM.brand_id.in_(brand_ids))
            )
            scan_count = int(scan_result.scalar() or 0)

        rows.append(OrgRow(
            org_id=org_id,
            name=org.name,
            email=org.email,
            plan=org.plan,
            is_demo=org.is_demo,
            onboarding_completed=org.onboarding_completed,
            created_at=org.created_at,
            total_spend_usd=total_spend,
            brand_count=brand_count,
            scan_job_count=scan_count,
        ))
    return rows


# ---------------------------------------------------------------------------
# GET /api/v1/admin/scan-jobs
# ---------------------------------------------------------------------------

@router.get("/scan-jobs", response_model=list[ScanJobRow], dependencies=[AdminDep])
async def list_all_scan_jobs(
    db: DbDep,
    status_filter: str | None = None,
    limit: int = 200,
) -> list[ScanJobRow]:
    """Recent scan jobs across all orgs."""
    from apps.api.models.brand import BrandORM

    q = (
        select(ScanJobORM, BrandORM.organization_id)
        .join(BrandORM, ScanJobORM.brand_id == BrandORM.id)
        .order_by(ScanJobORM.created_at.desc())
        .limit(limit)
    )
    if status_filter:
        q = q.where(ScanJobORM.status == status_filter)

    result = await db.execute(q)
    rows = result.all()

    return [
        ScanJobRow(
            job_id=str(job.id),
            org_id=org_id,
            brand_id=str(job.brand_id),
            job_type=job.job_type,
            status=job.status,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
        for job, org_id in rows
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/admin/costs
# ---------------------------------------------------------------------------

@router.get("/costs", response_model=list[CostPerOrgRow], dependencies=[AdminDep])
async def cost_per_org(db: DbDep, days: int = 30) -> list[CostPerOrgRow]:
    """Aggregated embedding spend per org for the last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(
            EmbeddingCostORM.org_id,
            func.sum(EmbeddingCostORM.cost_usd).label("total"),
            func.count().label("calls"),
            func.coalesce(func.sum(EmbeddingCostORM.tokens_input), 0).label("tokens"),
        )
        .where(EmbeddingCostORM.logged_at >= since)
        .group_by(EmbeddingCostORM.org_id)
        .order_by(func.sum(EmbeddingCostORM.cost_usd).desc())
    )
    return [
        CostPerOrgRow(
            org_id=row.org_id or "unknown",
            total_spend_usd=float(row.total or 0),
            api_calls=int(row.calls or 0),
            tokens_total=int(row.tokens or 0),
        )
        for row in result.all()
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/admin/nps
# ---------------------------------------------------------------------------

@router.get("/nps", response_model=list[NpsRow], dependencies=[AdminDep])
async def list_nps_responses(db: DbDep, limit: int = 500) -> list[NpsRow]:
    result = await db.execute(
        select(NpsResponseORM).order_by(NpsResponseORM.created_at.desc()).limit(limit)
    )
    return [
        NpsRow(
            org_id=n.organization_id,
            score=n.score,
            comment=n.comment,
            trigger=n.trigger,
            created_at=n.created_at,
        )
        for n in result.scalars().all()
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/admin/stats
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=AdminStatsResponse, dependencies=[AdminDep])
async def admin_stats(db: DbDep) -> AdminStatsResponse:
    total_orgs_result = await db.execute(
        select(func.count()).select_from(OrganizationORM).where(OrganizationORM.is_demo == False)  # noqa: E712
    )
    total_orgs = int(total_orgs_result.scalar() or 0)

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_result = await db.execute(
        select(func.count()).select_from(OrganizationORM).where(
            OrganizationORM.created_at >= seven_days_ago,
            OrganizationORM.is_demo == False,  # noqa: E712
        )
    )
    active_orgs_7d = int(active_result.scalar() or 0)

    avg_nps_result = await db.execute(
        select(func.avg(NpsResponseORM.score))
    )
    avg_nps_raw = avg_nps_result.scalar()
    avg_nps = float(avg_nps_raw) if avg_nps_raw is not None else None

    return AdminStatsResponse(
        total_orgs=total_orgs,
        active_orgs_7d=active_orgs_7d,
        avg_nps=avg_nps,
        p1_open_bugs=0,
    )
