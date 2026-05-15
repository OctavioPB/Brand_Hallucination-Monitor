"""InfraCostORM — DAG-level cost tagging for Airflow tasks."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from apps.api.database import Base


class InfraCostORM(Base):
    """Per-task Airflow cost record for cost-attribution dashboards."""

    __tablename__ = "infra_costs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    dag_run_id: Mapped[str] = mapped_column(String(255), nullable=False)
    dag_id: Mapped[str] = mapped_column(String(255), nullable=False)
    task_id: Mapped[str] = mapped_column(String(255), nullable=False)
    cost_component: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    units: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
