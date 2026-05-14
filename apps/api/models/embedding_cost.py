"""EmbeddingCost ORM and Pydantic model — tracks OpenAI API spend per job."""
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from apps.api.database import Base


class EmbeddingCostORM(Base):
    __tablename__ = "embedding_costs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dag_run_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="text-embedding-3-small")
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)  # brand_mention|competitor|intent_cluster
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_vectors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_cached: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmbeddingCostCreate(BaseModel):
    dag_run_id: str
    model: str = "text-embedding-3-small"
    job_type: str
    tokens_input: int = 0
    n_vectors: int = 0
    n_cached: int = 0
    cost_usd: Decimal = Field(default=Decimal("0"))


class EmbeddingCost(EmbeddingCostCreate):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    created_at: datetime
