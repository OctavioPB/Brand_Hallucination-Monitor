"""Convenience re-exports of all ORM models for Alembic autogenerate."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from apps.api.database import Base
from apps.api.models.brand import BrandORM
from apps.api.models.competitor import CompetitorORM
from apps.api.models.embedding_cost import EmbeddingCostORM
from apps.api.models.embedding_result import EmbeddingResultORM
from apps.api.models.scan_job import ScanJobORM
from apps.api.models.sps_score import SPSScoreORM


class IntentClusterORM(Base):
    """Pre-defined semantic intent clusters (e.g. 'reliability', 'innovation')."""

    __tablename__ = "intent_clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertORM(Base):
    """Hallucination and threshold alerts."""

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # LOW|MEDIUM|HIGH|CRITICAL
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(1024), nullable=False)
    acknowledged: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


__all__ = [
    "Base",
    "BrandORM",
    "CompetitorORM",
    "EmbeddingCostORM",
    "EmbeddingResultORM",
    "ScanJobORM",
    "SPSScoreORM",
    "IntentClusterORM",
    "AlertORM",
]
