"""Unit tests: Kafka event schema models."""
import hashlib
from datetime import datetime, timezone

import pytest

from apps.workers.kafka.schemas import (
    BrandMentionEvent,
    CompetitorMentionEvent,
    ReviewEvent,
    ReviewPlatform,
    SourceType,
)


class TestBrandMentionEvent:
    def test_content_hash_auto_computed(self):
        event = BrandMentionEvent(brand_name="Acme", raw_text="Hello Acme!", source_type=SourceType.MANUAL)
        expected = hashlib.sha256("Hello Acme!".encode()).hexdigest()
        assert event.content_hash == expected

    def test_explicit_content_hash_preserved(self):
        event = BrandMentionEvent(
            brand_name="Acme",
            raw_text="text",
            source_type=SourceType.RSS,
            content_hash="custom-hash",
        )
        assert event.content_hash == "custom-hash"

    def test_from_raw_text_factory(self):
        published = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
        event = BrandMentionEvent.from_raw_text(
            brand_name="Acme",
            raw_text="Acme launches new product",
            source_type=SourceType.RSS,
            source_url="https://example.com/article",
            published_at=published,
        )
        assert event.brand_name == "Acme"
        assert event.source_type == SourceType.RSS
        assert event.published_at == int(published.timestamp() * 1000)
        assert event.ingested_at > 0
        assert len(event.event_id) == 36  # UUID format

    def test_ingested_at_set_automatically(self):
        event = BrandMentionEvent(brand_name="X", raw_text="text", source_type=SourceType.MANUAL)
        assert event.ingested_at > 0

    def test_brand_id_defaults_empty(self):
        event = BrandMentionEvent(brand_name="X", raw_text="text", source_type=SourceType.MANUAL)
        assert event.brand_id == ""
        assert event.organization_id == ""


class TestReviewEvent:
    def test_rating_validation_in_range(self):
        review = ReviewEvent(
            platform=ReviewPlatform.TRUSTPILOT,
            review_id="abc123",
            body="Great product",
            rating=4.5,
        )
        assert review.rating == 4.5

    def test_rating_validation_out_of_range(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="rating must be in"):
            ReviewEvent(
                platform=ReviewPlatform.G2,
                review_id="x",
                body="text",
                rating=6.0,
            )

    def test_to_brand_mention_conversion(self):
        review = ReviewEvent(
            platform=ReviewPlatform.G2,
            review_id="g2-001",
            title="Excellent tool",
            body="This product is amazing for our workflow",
            rating=5.0,
        )
        mention = review.to_brand_mention("AcmeCorp")
        assert mention.brand_name == "AcmeCorp"
        assert mention.source_type == SourceType.REVIEW
        assert mention.source_id == "g2:g2-001"
        assert "Excellent tool" in mention.raw_text
        assert "amazing for our workflow" in mention.raw_text

    def test_content_hash_auto_computed_from_body(self):
        review = ReviewEvent(
            platform=ReviewPlatform.CAPTERRA,
            review_id="c001",
            body="Some review text",
        )
        expected = hashlib.sha256("Some review text".encode()).hexdigest()
        assert review.content_hash == expected


class TestSourceTypeEnum:
    def test_all_values(self):
        assert SourceType.RSS == "rss"
        assert SourceType.REDDIT == "reddit"
        assert SourceType.REVIEW == "review"
        assert SourceType.MANUAL == "manual"
        assert SourceType.UNKNOWN == "unknown"
