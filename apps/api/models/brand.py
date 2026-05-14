"""Brand domain models (Pydantic v2) and ORM mapping."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from apps.api.database import Base


# -----------------------------------------------------------------------
# ORM
# -----------------------------------------------------------------------
class BrandORM(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    manifest: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    competitors: Mapped[list["CompetitorORM"]] = relationship(  # type: ignore[name-defined]
        "CompetitorORM", back_populates="brand", cascade="all, delete-orphan"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# -----------------------------------------------------------------------
# Pydantic v2 schemas
# -----------------------------------------------------------------------
class BrandManifest(BaseModel):
    """Ground truth for what a brand is — and is not."""

    true_attributes: list[str] = Field(default_factory=list)
    false_attributes: list[str] = Field(default_factory=list)
    competitor_list: list[str] = Field(default_factory=list)
    regulatory_claims_to_avoid: list[str] = Field(default_factory=list)


class BrandCreate(BaseModel):
    organization_id: str
    name: str = Field(min_length=1, max_length=256)
    slug: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9-]+$")
    manifest: BrandManifest | None = None


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=256)
    manifest: BrandManifest | None = None


class Brand(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    organization_id: str
    name: str
    slug: str
    manifest: BrandManifest | None = None
    created_at: datetime
    updated_at: datetime
