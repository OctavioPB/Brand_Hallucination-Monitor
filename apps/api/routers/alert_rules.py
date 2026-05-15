"""Alert rules CRUD — customer-defined SPS threshold and competitor rank rules."""
from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.context import OrgContextDep
from apps.api.config import get_settings
from apps.api.database import get_db
from apps.api.models.report import AlertRuleORM
from apps.api.services.alert_rules import AlertRulesEngine

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/alert-rules", tags=["alert-rules"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

_VALID_RULE_TYPES = frozenset({"sps_threshold", "competitor_rank"})
_VALID_SEVERITIES = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})
_VALID_CLUSTERS = frozenset({
    "reliability", "innovation", "pricing_value",
    "market_leadership", "compliance", "support_quality",
})


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AlertRuleCreate(BaseModel):
    brand_id: uuid.UUID
    rule_type: str = Field(description="'sps_threshold' or 'competitor_rank'")
    cluster_slug: str | None = Field(default=None)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    competitor_name: str | None = Field(default=None, max_length=256)
    severity: str = Field(default="HIGH")

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        if v not in _VALID_RULE_TYPES:
            raise ValueError(f"rule_type must be one of {sorted(_VALID_RULE_TYPES)}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        v = v.upper()
        if v not in _VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {sorted(_VALID_SEVERITIES)}")
        return v

    @field_validator("cluster_slug")
    @classmethod
    def validate_cluster(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_CLUSTERS:
            raise ValueError(f"cluster_slug must be one of {sorted(_VALID_CLUSTERS)}")
        return v

    def validate_for_type(self) -> None:
        """Cross-field validation — call after creation."""
        if self.rule_type == "sps_threshold":
            if self.cluster_slug is None or self.threshold is None:
                raise ValueError(
                    "sps_threshold rules require both cluster_slug and threshold"
                )
        if self.rule_type == "competitor_rank":
            if self.competitor_name is None or self.cluster_slug is None:
                raise ValueError(
                    "competitor_rank rules require both competitor_name and cluster_slug"
                )


class AlertRuleUpdate(BaseModel):
    cluster_slug: str | None = None
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    competitor_name: str | None = None
    severity: str | None = None
    is_active: bool | None = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.upper()
            if v not in _VALID_SEVERITIES:
                raise ValueError(f"severity must be one of {sorted(_VALID_SEVERITIES)}")
        return v


class AlertRuleResponse(BaseModel):
    id: uuid.UUID
    organization_id: str
    brand_id: uuid.UUID
    rule_type: str
    cluster_slug: str | None
    threshold: float | None
    competitor_name: str | None
    severity: str
    is_active: bool
    created_at: str
    last_triggered_at: str | None


def _to_response(r: AlertRuleORM) -> AlertRuleResponse:
    return AlertRuleResponse(
        id=r.id,
        organization_id=r.organization_id,
        brand_id=r.brand_id,
        rule_type=r.rule_type,
        cluster_slug=r.cluster_slug,
        threshold=r.threshold,
        competitor_name=r.competitor_name,
        severity=r.severity,
        is_active=r.is_active,
        created_at=r.created_at.isoformat(),
        last_triggered_at=(r.last_triggered_at.isoformat() if r.last_triggered_at else None),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/alert-rules
# ---------------------------------------------------------------------------

@router.get("", response_model=list[AlertRuleResponse])
async def list_alert_rules(
    org_ctx: OrgContextDep,
    db: DbDep,
    brand_id: uuid.UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
) -> list[AlertRuleResponse]:
    q = (
        select(AlertRuleORM)
        .where(AlertRuleORM.organization_id == org_ctx.organization_id)
        .order_by(AlertRuleORM.created_at.desc())
    )
    if brand_id is not None:
        q = q.where(AlertRuleORM.brand_id == brand_id)
    if is_active is not None:
        q = q.where(AlertRuleORM.is_active == is_active)

    result = await db.execute(q)
    return [_to_response(r) for r in result.scalars().all()]


# ---------------------------------------------------------------------------
# POST /api/v1/alert-rules
# ---------------------------------------------------------------------------

@router.post("", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    payload: AlertRuleCreate,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> AlertRuleResponse:
    try:
        payload.validate_for_type()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    rule = AlertRuleORM(
        id=uuid.uuid4(),
        organization_id=org_ctx.organization_id,
        brand_id=payload.brand_id,
        rule_type=payload.rule_type,
        cluster_slug=payload.cluster_slug,
        threshold=payload.threshold,
        competitor_name=payload.competitor_name,
        severity=payload.severity,
        is_active=True,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    logger.info(
        "Alert rule created",
        rule_id=str(rule.id),
        rule_type=rule.rule_type,
        org_id=org_ctx.organization_id,
    )
    return _to_response(rule)


# ---------------------------------------------------------------------------
# PUT /api/v1/alert-rules/{rule_id}
# ---------------------------------------------------------------------------

@router.put("/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: uuid.UUID,
    payload: AlertRuleUpdate,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> AlertRuleResponse:
    result = await db.execute(
        select(AlertRuleORM).where(
            AlertRuleORM.id == rule_id,
            AlertRuleORM.organization_id == org_ctx.organization_id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")

    if payload.cluster_slug is not None:
        rule.cluster_slug = payload.cluster_slug
    if payload.threshold is not None:
        rule.threshold = payload.threshold
    if payload.competitor_name is not None:
        rule.competitor_name = payload.competitor_name
    if payload.severity is not None:
        rule.severity = payload.severity
    if payload.is_active is not None:
        rule.is_active = payload.is_active

    await db.commit()
    await db.refresh(rule)
    return _to_response(rule)


# ---------------------------------------------------------------------------
# DELETE /api/v1/alert-rules/{rule_id}
# ---------------------------------------------------------------------------

@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> None:
    result = await db.execute(
        select(AlertRuleORM).where(
            AlertRuleORM.id == rule_id,
            AlertRuleORM.organization_id == org_ctx.organization_id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")

    await db.delete(rule)
    await db.commit()
    logger.info("Alert rule deleted", rule_id=str(rule_id), org_id=org_ctx.organization_id)


# ---------------------------------------------------------------------------
# POST /api/v1/alert-rules/evaluate — manual trigger
# ---------------------------------------------------------------------------

@router.post("/evaluate", status_code=status.HTTP_200_OK)
async def evaluate_rules(
    org_ctx: OrgContextDep,
    db: DbDep,
    brand_id: uuid.UUID | None = Query(default=None),
) -> dict[str, int]:
    """Manually trigger rule evaluation for the org (or a specific brand).

    Returns the count of alerts fired.
    """
    settings = get_settings()
    engine = AlertRulesEngine(db, settings)

    if brand_id is not None:
        fired = await engine.evaluate_brand(org_ctx.organization_id, brand_id)
    else:
        fired = await engine.evaluate_all(org_ctx.organization_id)

    return {"alerts_fired": len(fired)}
