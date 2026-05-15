"""Cost tracking endpoints — $/brand/month breakdown for dashboard widget.

GET /api/v1/costs/summary   — today's spend vs. daily budget cap
GET /api/v1/costs/breakdown — per-day / per-brand / per-job-type (last 30 days)
GET /api/v1/costs/infra     — per-DAG-run Airflow cost records
"""
from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.context import OrgContextDep
from apps.api.database import get_db
from apps.api.models.embedding_cost import EmbeddingCostORM
from apps.api.models.infra_cost import InfraCostORM

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/costs", tags=["costs"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CostSummary(BaseModel):
    date: str
    total_cost_usd: float
    budget_cap_usd: float
    budget_remaining_usd: float
    budget_used_pct: float
    api_calls: int
    tokens_consumed: int
    vectors_from_cache: int


class CostBreakdownRow(BaseModel):
    day: str
    job_type: str
    cost_usd: float
    tokens: int
    calls: int


class InfraCostRow(BaseModel):
    dag_run_id: str
    dag_id: str
    task_id: str
    cost_component: str
    model: str | None
    cost_usd: float
    recorded_at: str


# ---------------------------------------------------------------------------
# GET /api/v1/costs/summary
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=CostSummary)
async def get_cost_summary(
    org_ctx: OrgContextDep,
    db: DbDep,
) -> CostSummary:
    """Today's embedding spend vs. the configured daily budget cap."""
    from apps.api.config import get_settings
    from datetime import date, datetime, timezone

    settings = get_settings()
    today = date.today()

    result = await db.execute(
        select(
            func.coalesce(func.sum(EmbeddingCostORM.cost_usd), 0).label("total"),
            func.count(EmbeddingCostORM.id).label("calls"),
            func.coalesce(func.sum(EmbeddingCostORM.tokens_input), 0).label("tokens"),
            func.coalesce(func.sum(EmbeddingCostORM.n_cached), 0).label("cached"),
        ).where(
            EmbeddingCostORM.org_id == org_ctx.organization_id,
            func.date(EmbeddingCostORM.logged_at) == today,
        )
    )
    row = result.one()
    total = float(row.total or 0)
    cap = settings.max_daily_spend_usd

    return CostSummary(
        date=today.isoformat(),
        total_cost_usd=total,
        budget_cap_usd=cap,
        budget_remaining_usd=max(0.0, cap - total),
        budget_used_pct=round(total / cap * 100, 1) if cap > 0 else 0.0,
        api_calls=row.calls or 0,
        tokens_consumed=row.tokens or 0,
        vectors_from_cache=row.cached or 0,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/costs/breakdown
# ---------------------------------------------------------------------------

@router.get("/breakdown", response_model=list[CostBreakdownRow])
async def get_cost_breakdown(
    org_ctx: OrgContextDep,
    db: DbDep,
    days: int = Query(30, ge=1, le=90, description="Rolling window in days"),
) -> list[CostBreakdownRow]:
    """Per-day per-job-type cost breakdown for the past N days."""
    result = await db.execute(
        select(
            func.date(EmbeddingCostORM.logged_at).label("day"),
            EmbeddingCostORM.job_type,
            func.sum(EmbeddingCostORM.cost_usd).label("cost_usd"),
            func.sum(EmbeddingCostORM.tokens_input).label("tokens"),
            func.count(EmbeddingCostORM.id).label("calls"),
        )
        .where(
            EmbeddingCostORM.org_id == org_ctx.organization_id,
            EmbeddingCostORM.logged_at >= text(f"NOW() - INTERVAL '{days} days'"),
        )
        .group_by(
            func.date(EmbeddingCostORM.logged_at),
            EmbeddingCostORM.job_type,
        )
        .order_by(text("day DESC"), text("cost_usd DESC"))
    )
    return [
        CostBreakdownRow(
            day=str(r.day),
            job_type=r.job_type or "unknown",
            cost_usd=float(r.cost_usd or 0),
            tokens=r.tokens or 0,
            calls=r.calls or 0,
        )
        for r in result.all()
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/costs/infra
# ---------------------------------------------------------------------------

@router.get("/infra", response_model=list[InfraCostRow])
async def get_infra_costs(
    org_ctx: OrgContextDep,
    db: DbDep,
    days: int = Query(7, ge=1, le=30),
) -> list[InfraCostRow]:
    """DAG-level Airflow cost records (task-level cost tagging)."""
    result = await db.execute(
        select(InfraCostORM)
        .where(
            InfraCostORM.organization_id == org_ctx.organization_id,
            InfraCostORM.recorded_at >= text(f"NOW() - INTERVAL '{days} days'"),
        )
        .order_by(InfraCostORM.recorded_at.desc())
        .limit(200)
    )
    rows = result.scalars().all()
    return [
        InfraCostRow(
            dag_run_id=r.dag_run_id,
            dag_id=r.dag_id,
            task_id=r.task_id,
            cost_component=r.cost_component,
            model=r.model,
            cost_usd=float(r.cost_usd or 0),
            recorded_at=r.recorded_at.isoformat(),
        )
        for r in rows
    ]
