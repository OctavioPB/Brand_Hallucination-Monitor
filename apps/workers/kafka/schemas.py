"""Pydantic v2 event models — mirror the Avro schemas in infra/kafka/schemas/.

These are the Python-native representation of every Kafka event. Producers
build these objects; consumers parse raw bytes into these objects.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------
class SourceType(StrEnum):
    RSS = "rss"
    REDDIT = "reddit"
    REVIEW = "review"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class SentimentHint(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class ReviewPlatform(StrEnum):
    G2 = "g2"
    CAPTERRA = "capterra"
    TRUSTPILOT = "trustpilot"
    APPSTORE = "appstore"
    PLAYSTORE = "playstore"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Event models
# ---------------------------------------------------------------------------
class BrandMentionEvent(BaseModel):
    """Matches brand_mention_event.avsc — published to brand.mentions.raw."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str = ""                 # set by enrichment consumer; empty until enriched
    brand_name: str
    organization_id: str = ""          # set by enrichment consumer
    source_type: SourceType
    source_url: str | None = None
    source_id: str | None = None
    title: str | None = None
    raw_text: str
    content_hash: str = ""             # auto-computed from raw_text if empty
    published_at: int | None = None    # epoch ms
    ingested_at: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000)
    )
    schema_version: str = "1.0.0"

    def model_post_init(self, __context: object) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.raw_text.encode()).hexdigest()

    @classmethod
    def from_raw_text(
        cls,
        *,
        brand_name: str,
        raw_text: str,
        source_type: SourceType,
        source_url: str | None = None,
        source_id: str | None = None,
        title: str | None = None,
        published_at: datetime | None = None,
    ) -> "BrandMentionEvent":
        return cls(
            brand_name=brand_name,
            raw_text=raw_text,
            source_type=source_type,
            source_url=source_url,
            source_id=source_id,
            title=title,
            published_at=int(published_at.timestamp() * 1000) if published_at else None,
        )


class CompetitorMentionEvent(BaseModel):
    """Matches competitor_mention_event.avsc — published to competitor.mentions.raw."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str = ""
    organization_id: str = ""
    competitor_name: str
    competitor_id: str | None = None
    source_type: SourceType
    source_url: str | None = None
    source_id: str | None = None
    title: str | None = None
    raw_text: str
    content_hash: str = ""
    sentiment_hint: SentimentHint = SentimentHint.UNKNOWN
    published_at: int | None = None
    ingested_at: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000)
    )
    schema_version: str = "1.0.0"

    def model_post_init(self, __context: object) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.raw_text.encode()).hexdigest()


class ReviewEvent(BaseModel):
    """Matches review_event.avsc — published to brand.mentions.raw as a review subtype."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str = ""
    organization_id: str = ""
    platform: ReviewPlatform
    review_id: str
    reviewer_handle: str | None = None
    title: str | None = None
    body: str
    rating: float | None = None
    verified_purchase: bool = False
    source_url: str | None = None
    content_hash: str = ""
    published_at: int | None = None
    ingested_at: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000)
    )
    schema_version: str = "1.0.0"

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v: float | None) -> float | None:
        if v is not None and not (1.0 <= v <= 5.0):
            raise ValueError(f"rating must be in [1.0, 5.0], got {v}")
        return v

    def model_post_init(self, __context: object) -> None:
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.body.encode()).hexdigest()

    def to_brand_mention(self, brand_name: str) -> BrandMentionEvent:
        """Convert a ReviewEvent to a BrandMentionEvent for the unified pipeline."""
        return BrandMentionEvent(
            brand_name=brand_name,
            raw_text=f"{self.title or ''}\n{self.body}".strip(),
            source_type=SourceType.REVIEW,
            source_url=self.source_url,
            source_id=f"{self.platform.value}:{self.review_id}",
            title=self.title,
            published_at=self.published_at,
        )
