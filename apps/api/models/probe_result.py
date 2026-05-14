"""ProbeResult ORM — persists each LLM probe call for audit trail."""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from apps.api.database import Base


class ProbeResultORM(Base):
    __tablename__ = "probe_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    probe_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    llm_response: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=Decimal("0"))
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hallucinations_detected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dag_run_id: Mapped[str] = mapped_column(String(256), nullable=False, default="manual")
    probed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
