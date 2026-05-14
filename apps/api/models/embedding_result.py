"""EmbeddingResult domain models (Pydantic v2) and ORM mapping."""
import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from apps.api.database import Base


class EmbeddingStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


# -----------------------------------------------------------------------
# ORM — stores embedding metadata (vectors live in Qdrant)
# -----------------------------------------------------------------------
class EmbeddingResultORM(Base):
    __tablename__ = "embedding_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    source_text_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False, default="text-embedding-3-small")
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False, default=1536)
    qdrant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=EmbeddingStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# -----------------------------------------------------------------------
# Pydantic v2 schemas
# -----------------------------------------------------------------------
class EmbeddingResult(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    brand_id: uuid.UUID
    source_text_hash: str
    model: str
    dimensions: int
    qdrant_id: str | None
    tokens_used: int
    status: str
    created_at: datetime
