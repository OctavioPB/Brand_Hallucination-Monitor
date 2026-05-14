"""Competitor domain models (Pydantic v2) and ORM mapping."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from apps.api.database import Base


# -----------------------------------------------------------------------
# ORM
# -----------------------------------------------------------------------
class CompetitorORM(Base):
    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    competitor_name: Mapped[str] = mapped_column(String(256), nullable=False)
    competitor_slug: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    brand: Mapped["BrandORM"] = relationship("BrandORM", back_populates="competitors")  # type: ignore[name-defined]


# -----------------------------------------------------------------------
# Pydantic v2 schemas
# -----------------------------------------------------------------------
class CompetitorCreate(BaseModel):
    brand_id: uuid.UUID
    competitor_name: str = Field(min_length=1, max_length=256)
    competitor_slug: str | None = Field(default=None, max_length=128)


class Competitor(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    brand_id: uuid.UUID
    competitor_name: str
    competitor_slug: str | None
    created_at: datetime
