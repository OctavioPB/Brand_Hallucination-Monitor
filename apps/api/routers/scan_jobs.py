"""Scan job endpoints — trigger and monitor on-demand scans."""
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
from apps.api.models.scan_job import ScanJob, ScanJobCreate, ScanJobORM, ScanJobStatus

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/scan-jobs", tags=["scan-jobs"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _verify_brand_access(
    brand_id: uuid.UUID, org_ctx: OrgContextDep, db: AsyncSession
) -> None:
    result = await db.execute(
        select(BrandORM).where(
            BrandORM.id == brand_id,
            BrandORM.organization_id == org_ctx.organization_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")


# ---------------------------------------------------------------------------
# POST /api/v1/scan-jobs
# ---------------------------------------------------------------------------

@router.post("", response_model=ScanJob, status_code=status.HTTP_202_ACCEPTED)
async def trigger_scan_job(
    payload: ScanJobCreate,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> ScanJob:
    """Trigger an on-demand scan for a brand.

    Returns 202 Accepted immediately. Poll GET /scan-jobs/{id} for status.
    The actual work is enqueued to Celery.
    """
    await _verify_brand_access(payload.brand_id, org_ctx, db)

    job = ScanJobORM(
        id=uuid.uuid4(),
        brand_id=payload.brand_id,
        job_type=payload.job_type,
        status=ScanJobStatus.PENDING,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Best-effort Celery enqueue — fail-open so the job record is always created
    try:
        from apps.workers.tasks.scan import run_scan_job
        run_scan_job.delay(str(job.id), payload.job_type)
        logger.info(
            "Scan job enqueued",
            job_id=str(job.id),
            job_type=payload.job_type,
            org_id=org_ctx.organization_id,
        )
    except Exception:
        logger.warning("Celery enqueue failed — job created but not dispatched", job_id=str(job.id))

    return ScanJob.model_validate(job)


# ---------------------------------------------------------------------------
# GET /api/v1/scan-jobs/{job_id}
# ---------------------------------------------------------------------------

@router.get("/{job_id}", response_model=ScanJob)
async def get_scan_job(
    job_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> ScanJob:
    """Get status and result of a scan job. Org isolation via brand → org join."""
    result = await db.execute(
        select(ScanJobORM)
        .join(BrandORM, BrandORM.id == ScanJobORM.brand_id)
        .where(
            ScanJobORM.id == job_id,
            BrandORM.organization_id == org_ctx.organization_id,
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan job not found")

    return ScanJob.model_validate(job)
