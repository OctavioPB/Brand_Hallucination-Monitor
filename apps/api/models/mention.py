"""Mention API request/response models (Pydantic v2).

These are the API-layer schemas for the manual injection endpoint.
They map 1:1 to BrandMentionEvent (Kafka schema) but are kept separate
to allow independent versioning.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from apps.workers.kafka.schemas import SourceType


class MentionCreate(BaseModel):
    """Body for POST /api/v1/mentions — manual brand mention injection."""

    brand_name: str = Field(min_length=1, max_length=256)
    raw_text: str = Field(min_length=1, max_length=100_000)
    source_type: SourceType = SourceType.MANUAL
    source_url: str | None = Field(default=None, max_length=2048)
    source_id: str | None = Field(default=None, max_length=256)
    title: str | None = Field(default=None, max_length=512)
    published_at: datetime | None = None


class MentionResponse(BaseModel):
    event_id: str
    brand_name: str
    content_hash: str
    source_type: str
    status: str = "queued"
    message: str = "Mention accepted and queued for processing."
