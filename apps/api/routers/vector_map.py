"""Vector map endpoints — 2D semantic position for visualization.

GET  /api/v1/brands/{id}/vector-map        — current snapshot (Redis-cached, 1h TTL)
GET  /api/v1/brands/{id}/vector-map/stream — SSE live updates (30s interval)

The 2D coordinates are derived from SPS scores across all intent clusters.
Sprint 9 adds Redis caching so repeated GET requests within 1 hour are served
from cache instead of hitting the DB on every call (target: < 200ms P95).
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Annotated, AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.context import OrgContextDep
from apps.api.database import get_db
from apps.api.models.brand import BrandORM
from apps.api.models.sps_score import SPSScoreORM

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/brands", tags=["vector-map"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

_SSE_INTERVAL_SECONDS = 30
_CACHE_TTL_SECONDS = 3_600  # 1 hour — SPS scores update at most once per Airflow run


def _cache_key(brand_id: uuid.UUID, org_id: str) -> str:
    return f"vmap:v1:{org_id}:{brand_id}"


def _get_redis():
    """Return a Redis client from config. Returns None if Redis is unavailable."""
    try:
        import redis as redis_lib
        from apps.api.config import get_settings
        return redis_lib.from_url(get_settings().redis_url, decode_responses=True)
    except Exception:
        return None


class VectorPoint(BaseModel):
    label: str
    x: float = Field(ge=-1.0, le=1.0)
    y: float = Field(ge=-1.0, le=1.0)
    cluster_slug: str
    score: float = Field(ge=0.0, le=1.0)


class VectorMapSnapshot(BaseModel):
    brand_id: str
    brand_name: str
    points: list[VectorPoint]
    generated_at: str


async def _build_snapshot(
    brand_id: uuid.UUID, org_ctx: OrgContextDep, db: AsyncSession
) -> VectorMapSnapshot:
    result = await db.execute(
        select(BrandORM).where(
            BrandORM.id == brand_id,
            BrandORM.organization_id == org_ctx.organization_id,
        )
    )
    brand = result.scalar_one_or_none()
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")

    # Fetch latest SPS score per intent cluster
    from sqlalchemy import func, text

    subq = (
        select(
            SPSScoreORM.intent_cluster_slug,
            func.max(SPSScoreORM.calculated_at).label("latest_at"),
        )
        .where(SPSScoreORM.brand_id == brand_id)
        .group_by(SPSScoreORM.intent_cluster_slug)
        .subquery()
    )

    scores_result = await db.execute(
        select(SPSScoreORM).join(
            subq,
            (SPSScoreORM.intent_cluster_slug == subq.c.intent_cluster_slug)
            & (SPSScoreORM.calculated_at == subq.c.latest_at),
        ).where(SPSScoreORM.brand_id == brand_id)
    )
    scores = scores_result.scalars().all()

    # Map clusters to (x, y) positions using a fixed layout.
    # For the dashboard MVP this is sufficient; the full t-SNE pipeline (Sprint 9)
    # will replace these with computed coordinates from Qdrant vectors.
    _CLUSTER_POSITIONS: dict[str, tuple[float, float]] = {
        "reliability":      (-0.6,  0.5),
        "innovation":       ( 0.7,  0.6),
        "pricing_value":    (-0.5, -0.6),
        "market_leadership":( 0.6, -0.4),
        "compliance":       (-0.8, -0.1),
        "support_quality":  ( 0.2,  0.8),
    }

    from datetime import datetime, timezone
    points = []
    for s in scores:
        x, y = _CLUSTER_POSITIONS.get(s.intent_cluster_slug, (0.0, 0.0))
        # Scale position by score so brands closer to the origin are weaker
        scaled_x = round(x * s.score, 4)
        scaled_y = round(y * s.score, 4)
        points.append(
            VectorPoint(
                label=s.intent_cluster_slug.replace("_", " ").title(),
                x=scaled_x,
                y=scaled_y,
                cluster_slug=s.intent_cluster_slug,
                score=s.score,
            )
        )

    return VectorMapSnapshot(
        brand_id=str(brand_id),
        brand_name=brand.name,
        points=points,
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/brands/{brand_id}/vector-map
# ---------------------------------------------------------------------------

@router.get("/{brand_id}/vector-map", response_model=VectorMapSnapshot)
async def get_vector_map(
    brand_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> VectorMapSnapshot:
    """Return current 2D semantic position snapshot for a brand (Redis-cached 1h)."""
    redis = _get_redis()
    key = _cache_key(brand_id, org_ctx.organization_id)

    # Try cache first
    if redis is not None:
        try:
            raw = redis.get(key)
            if raw:
                return VectorMapSnapshot.model_validate_json(raw)
        except Exception:
            logger.warning("Vector map cache read failed", brand_id=str(brand_id))

    snapshot = await _build_snapshot(brand_id, org_ctx, db)

    # Write to cache (best-effort, non-blocking)
    if redis is not None:
        try:
            redis.set(key, snapshot.model_dump_json(), ex=_CACHE_TTL_SECONDS)
        except Exception:
            logger.warning("Vector map cache write failed", brand_id=str(brand_id))

    return snapshot


# ---------------------------------------------------------------------------
# GET /api/v1/brands/{brand_id}/vector-map/stream  (SSE)
# ---------------------------------------------------------------------------

@router.get("/{brand_id}/vector-map/stream")
async def stream_vector_map(
    brand_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
    request: Request,
) -> StreamingResponse:
    """Server-Sent Events stream that re-emits the vector map every 30 seconds."""

    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            if await request.is_disconnected():
                break
            try:
                snapshot = await _build_snapshot(brand_id, org_ctx, db)
                data = snapshot.model_dump_json()
                yield f"event: vector_map\ndata: {data}\n\n"
            except HTTPException as exc:
                yield f"event: error\ndata: {json.dumps({'detail': exc.detail})}\n\n"
                break
            except Exception:
                logger.exception("SSE vector map error", brand_id=str(brand_id))
                yield f"event: error\ndata: {json.dumps({'detail': 'stream error'})}\n\n"
                break

            await asyncio.sleep(_SSE_INTERVAL_SECONDS)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
