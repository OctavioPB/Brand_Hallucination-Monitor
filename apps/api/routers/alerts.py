"""Alert management endpoints."""
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
from apps.api.models.db import AlertORM
from apps.api.models.webhook import WebhookEndpointORM

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class AlertResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    organization_id: str
    brand_id: uuid.UUID
    severity: str
    alert_type: str
    message: str
    acknowledged: bool
    created_at: str


class WebhookCreate(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    name: str = Field(min_length=1, max_length=128)
    severity_filter: str = Field(default="CRITICAL,HIGH", max_length=64)


class WebhookResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    organization_id: str
    url: str
    name: str
    severity_filter: str
    is_active: bool


# ---------------------------------------------------------------------------
# GET /api/v1/alerts
# ---------------------------------------------------------------------------

@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    org_ctx: OrgContextDep,
    db: DbDep,
    severity: str | None = Query(default=None),
    acknowledged: bool | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AlertResponse]:
    """Paginated list of alerts for the caller's organization."""
    query = (
        select(AlertORM)
        .where(AlertORM.organization_id == org_ctx.organization_id)
        .order_by(AlertORM.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if severity:
        query = query.where(AlertORM.severity == severity.upper())
    if acknowledged is not None:
        query = query.where(AlertORM.acknowledged == acknowledged)

    result = await db.execute(query)
    alerts = result.scalars().all()

    return [
        AlertResponse(
            id=a.id,
            organization_id=a.organization_id,
            brand_id=a.brand_id,
            severity=a.severity,
            alert_type=a.alert_type,
            message=a.message,
            acknowledged=a.acknowledged,
            created_at=a.created_at.isoformat(),
        )
        for a in alerts
    ]


# ---------------------------------------------------------------------------
# PATCH /api/v1/alerts/{alert_id}/acknowledge
# ---------------------------------------------------------------------------

@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> AlertResponse:
    """Mark an alert as acknowledged."""
    result = await db.execute(
        select(AlertORM).where(
            AlertORM.id == alert_id,
            AlertORM.organization_id == org_ctx.organization_id,
        )
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.acknowledged = True
    await db.commit()
    await db.refresh(alert)

    return AlertResponse(
        id=alert.id,
        organization_id=alert.organization_id,
        brand_id=alert.brand_id,
        severity=alert.severity,
        alert_type=alert.alert_type,
        message=alert.message,
        acknowledged=alert.acknowledged,
        created_at=alert.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/alerts/webhooks
# ---------------------------------------------------------------------------

@router.post(
    "/webhooks",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_webhook(
    payload: WebhookCreate,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> WebhookResponse:
    """Register a webhook endpoint to receive alert notifications."""
    webhook = WebhookEndpointORM(
        id=uuid.uuid4(),
        organization_id=org_ctx.organization_id,
        url=payload.url,
        name=payload.name,
        severity_filter=payload.severity_filter,
        is_active=True,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)

    logger.info(
        "Webhook registered",
        org_id=org_ctx.organization_id,
        webhook_id=str(webhook.id),
        severity_filter=payload.severity_filter,
    )
    return WebhookResponse.model_validate(webhook)


# ---------------------------------------------------------------------------
# GET /api/v1/alerts/webhooks
# ---------------------------------------------------------------------------

@router.get("/webhooks", response_model=list[WebhookResponse])
async def list_webhooks(org_ctx: OrgContextDep, db: DbDep) -> list[WebhookResponse]:
    """List webhook endpoints for the caller's organization."""
    result = await db.execute(
        select(WebhookEndpointORM)
        .where(WebhookEndpointORM.organization_id == org_ctx.organization_id)
        .order_by(WebhookEndpointORM.created_at.desc())
    )
    return [WebhookResponse.model_validate(w) for w in result.scalars().all()]
