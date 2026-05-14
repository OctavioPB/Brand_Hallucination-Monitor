"""SPSScore ORM — Semantic Proximity Score time-series per brand × intent cluster."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from apps.api.database import Base


class SPSScoreORM(Base):
    __tablename__ = "sps_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    intent_cluster_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="text-embedding-3-small"
    )
    dag_run_id: Mapped[str] = mapped_column(String(256), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class SPSScoreCreate(BaseModel):
    brand_id: uuid.UUID
    intent_cluster_slug: str
    score: float = Field(ge=0.0, le=1.0)
    model_version: str = "text-embedding-3-small"
    dag_run_id: str


class SPSScore(SPSScoreCreate):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    calculated_at: datetime
