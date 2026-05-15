"""Report, AlertRule, and AlertNotification ORM models."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from apps.api.database import Base


class ReportORM(Base):
    """Generated brand safety report — weekly or on-demand."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'weekly' | 'on_demand'
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # PDF rendered bytes — null until explicitly generated
    pdf_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # Comma-separated email addresses the report was sent to
    emailed_to: Mapped[str | None] = mapped_column(Text, nullable=True)
    week_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class AlertRuleORM(Base):
    """Customer-defined threshold rule for generating alerts automatically."""

    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # 'sps_threshold' → fires when SPS for cluster_slug falls below threshold
    # 'competitor_rank' → fires when competitor_name appears in a cluster's top associations
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    cluster_slug: Mapped[str | None] = mapped_column(String(64), nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    competitor_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="HIGH")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Tracks when this rule last fired to enable cooldown logic
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AlertNotificationORM(Base):
    """Delivery log for a single alert dispatch attempt (per channel)."""

    __tablename__ = "alert_notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # 'webhook' | 'slack' | 'email'
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    # URL for webhook/slack, email address for email channel
    recipient: Mapped[str] = mapped_column(String(1024), nullable=False)
    # 'pending' | 'sent' | 'failed'
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
