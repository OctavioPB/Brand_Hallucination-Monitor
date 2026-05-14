"""ScanJob domain models (Pydantic v2) and ORM mapping."""
import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from apps.api.database import Base


class ScanJobType(StrEnum):
    FULL = "full"
    LLM_PROBE = "llm_probe"
    EMBEDDING_REFRESH = "embedding_refresh"
    COMPETITOR_BENCHMARK = "competitor_benchmark"


class ScanJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# -----------------------------------------------------------------------
# ORM
# -----------------------------------------------------------------------
class ScanJobORM(Base):
    __tablename__ = "scan_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ScanJobStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# -----------------------------------------------------------------------
# Pydantic v2 schemas
# -----------------------------------------------------------------------
class ScanJobCreate(BaseModel):
    brand_id: uuid.UUID
    job_type: ScanJobType = ScanJobType.FULL


class ScanJob(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    brand_id: uuid.UUID
    job_type: str
    status: str
    error_message: str | None = None
    result: dict | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
