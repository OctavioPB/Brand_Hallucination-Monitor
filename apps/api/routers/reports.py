"""Report management endpoints + compliance JSONL export."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, AsyncIterator

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.context import OrgContextDep
from apps.api.config import get_settings
from apps.api.database import get_db
from apps.api.models.brand import BrandORM
from apps.api.models.db import AlertORM
from apps.api.models.probe_result import ProbeResultORM
from apps.api.models.report import ReportORM
from apps.api.models.sps_score import SPSScoreORM
from apps.api.services.report_generator import ReportGenerator

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ReportSummary(BaseModel):
    """Lightweight list-view of a report — does not include content_json or pdf_bytes."""

    id: uuid.UUID
    organization_id: str
    brand_id: uuid.UUID
    report_type: str
    title: str
    week_start: date | None
    generated_at: str
    has_pdf: bool


class ReportDetail(ReportSummary):
    content_json: dict


class GenerateReportRequest(BaseModel):
    brand_id: uuid.UUID
    week_start: date | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_summary(r: ReportORM) -> ReportSummary:
    return ReportSummary(
        id=r.id,
        organization_id=r.organization_id,
        brand_id=r.brand_id,
        report_type=r.report_type,
        title=r.title,
        week_start=r.week_start,
        generated_at=r.generated_at.isoformat(),
        has_pdf=r.pdf_bytes is not None,
    )


async def _get_brand_or_404(
    brand_id: uuid.UUID, org_id: str, db: AsyncSession
) -> BrandORM:
    result = await db.execute(
        select(BrandORM).where(
            BrandORM.id == brand_id,
            BrandORM.organization_id == org_id,
        )
    )
    brand = result.scalar_one_or_none()
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return brand


# ---------------------------------------------------------------------------
# GET /api/v1/reports
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ReportSummary])
async def list_reports(
    org_ctx: OrgContextDep,
    db: DbDep,
    brand_id: uuid.UUID | None = Query(default=None),
    report_type: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[ReportSummary]:
    """List generated reports for the caller's org, newest first."""
    q = (
        select(ReportORM)
        .where(ReportORM.organization_id == org_ctx.organization_id)
        .order_by(ReportORM.generated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if brand_id is not None:
        q = q.where(ReportORM.brand_id == brand_id)
    if report_type is not None:
        q = q.where(ReportORM.report_type == report_type)

    result = await db.execute(q)
    return [_to_summary(r) for r in result.scalars().all()]


# ---------------------------------------------------------------------------
# GET /api/v1/reports/{report_id}
# ---------------------------------------------------------------------------

@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> ReportDetail:
    """Full report JSON including content_json."""
    result = await db.execute(
        select(ReportORM).where(
            ReportORM.id == report_id,
            ReportORM.organization_id == org_ctx.organization_id,
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return ReportDetail(
        **_to_summary(report).model_dump(),
        content_json=report.content_json,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/reports/{report_id}/download
# ---------------------------------------------------------------------------

@router.get("/{report_id}/download")
async def download_report_pdf(
    report_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> Response:
    """Download the pre-rendered PDF for a report."""
    result = await db.execute(
        select(ReportORM).where(
            ReportORM.id == report_id,
            ReportORM.organization_id == org_ctx.organization_id,
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if not report.pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not available for this report",
        )

    safe_title = report.title.replace(" ", "_").replace("/", "-")[:64]
    return Response(
        content=report.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_title}.pdf"',
            "Content-Length": str(len(report.pdf_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# POST /api/v1/reports/generate — on-demand report trigger
# ---------------------------------------------------------------------------

@router.post(
    "/generate",
    response_model=ReportSummary,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_report(
    payload: GenerateReportRequest,
    org_ctx: OrgContextDep,
    db: DbDep,
    background_tasks: BackgroundTasks,
) -> ReportSummary:
    """Trigger an on-demand report. Returns 202; generation runs in background."""
    brand = await _get_brand_or_404(payload.brand_id, org_ctx.organization_id, db)

    # Create a placeholder row immediately so the caller gets an ID
    placeholder = ReportORM(
        id=uuid.uuid4(),
        organization_id=org_ctx.organization_id,
        brand_id=payload.brand_id,
        report_type="on_demand",
        title=f"On-Demand Report — {brand.name}",
        content_json={},
        week_start=payload.week_start,
    )
    db.add(placeholder)
    await db.commit()
    await db.refresh(placeholder)

    report_id = placeholder.id

    async def _generate() -> None:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
        from apps.api.config import get_settings as _get_settings

        s = _get_settings()
        engine = create_async_engine(s.database_url, echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with session_factory() as session:
            generator = ReportGenerator(session)
            report = await generator.generate_weekly(
                brand_id=payload.brand_id,
                organization_id=org_ctx.organization_id,
                brand_name=brand.name,
                week_start=payload.week_start,
            )
            # Update the placeholder row with real content
            placeholder_result = await session.execute(
                select(ReportORM).where(ReportORM.id == report_id)
            )
            target = placeholder_result.scalar_one_or_none()
            if target is not None:
                target.content_json = report.content_json
                target.pdf_bytes = report.pdf_bytes
                target.title = report.title
                await session.commit()

        await engine.dispose()

    background_tasks.add_task(_generate)

    logger.info(
        "On-demand report triggered",
        brand_id=str(payload.brand_id),
        report_id=str(report_id),
    )
    return _to_summary(placeholder)


# ---------------------------------------------------------------------------
# GET /api/v1/brands/{brand_id}/compliance-export
# ---------------------------------------------------------------------------

compliance_router = APIRouter(prefix="/api/v1/brands", tags=["compliance"])


@compliance_router.get("/{brand_id}/compliance-export")
async def compliance_export(
    brand_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> StreamingResponse:
    """JSONL export: all probe results + SPS scores + manifest versions.

    Each line is a valid JSON object. Three record types:
    - {"type": "probe_result", ...}
    - {"type": "sps_score", ...}
    - {"type": "brand_manifest", ...}

    Suitable as regulatory/legal evidence that an AI model was making false claims.
    """
    brand = await _get_brand_or_404(brand_id, org_ctx.organization_id, db)

    async def _stream() -> AsyncIterator[str]:
        import json

        # ---- Brand manifest snapshot ----
        yield json.dumps({
            "type": "brand_manifest",
            "brand_id": str(brand.id),
            "brand_name": brand.name,
            "organization_id": brand.organization_id,
            "manifest": brand.manifest,
            "exported_at": date.today().isoformat(),
        }) + "\n"

        # ---- Probe results ----
        probes_result = await db.execute(
            select(ProbeResultORM)
            .where(ProbeResultORM.brand_id == brand_id)
            .order_by(ProbeResultORM.probed_at.asc())
        )
        for probe in probes_result.scalars().all():
            yield json.dumps({
                "type": "probe_result",
                "id": str(probe.id),
                "brand_id": str(probe.brand_id),
                "model_name": probe.model_name,
                "probe_prompt": probe.probe_prompt,
                "llm_response": probe.llm_response,
                "hallucinations_detected": probe.hallucinations_detected,
                "cost_usd": float(probe.cost_usd),
                "dag_run_id": probe.dag_run_id,
                "probed_at": probe.probed_at.isoformat(),
            }) + "\n"

        # ---- SPS scores ----
        sps_result = await db.execute(
            select(SPSScoreORM)
            .where(SPSScoreORM.brand_id == brand_id)
            .order_by(SPSScoreORM.calculated_at.asc())
        )
        for sps in sps_result.scalars().all():
            yield json.dumps({
                "type": "sps_score",
                "id": str(sps.id),
                "brand_id": str(sps.brand_id),
                "intent_cluster_slug": sps.intent_cluster_slug,
                "score": sps.score,
                "model_version": sps.model_version,
                "dag_run_id": sps.dag_run_id,
                "calculated_at": sps.calculated_at.isoformat(),
            }) + "\n"

        # ---- Alerts ----
        alerts_result = await db.execute(
            select(AlertORM)
            .where(AlertORM.brand_id == brand_id)
            .order_by(AlertORM.created_at.asc())
        )
        for alert in alerts_result.scalars().all():
            yield json.dumps({
                "type": "alert",
                "id": str(alert.id),
                "brand_id": str(alert.brand_id),
                "severity": alert.severity,
                "alert_type": alert.alert_type,
                "message": alert.message,
                "acknowledged": alert.acknowledged,
                "created_at": alert.created_at.isoformat(),
            }) + "\n"

    logger.info(
        "Compliance export requested",
        brand_id=str(brand_id),
        org_id=org_ctx.organization_id,
    )

    filename = f"compliance_export_{brand.slug}_{date.today().isoformat()}.jsonl"
    return StreamingResponse(
        _stream(),
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Brand": brand.slug,
        },
    )
