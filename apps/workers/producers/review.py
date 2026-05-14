"""Review Scraper Producer — fetches reviews from G2, Capterra, and Trustpilot.

Sources:
- Trustpilot: public RSS feed per business (no scraping required)
- G2: public RSS feed (g2.com/products/{slug}/reviews.atom)
- Capterra: no public RSS — uses a configurable webhook URL or is skipped

Design rule (PLAN.md risk register): we only consume *public* RSS feeds and
platform-provided APIs. We never bypass robots.txt or ToS-protected content.
If a platform removes its public feed, the producer falls back to no-op with
a WARNING log.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import structlog

from apps.workers.kafka.schemas import ReviewEvent, ReviewPlatform, SourceType
from apps.workers.producers.base import BaseProducer, ProducerConfig

logger = structlog.get_logger(__name__)


@dataclass
class ReviewFeedConfig:
    platform: ReviewPlatform
    feed_url: str
    # Optional: override how rating is extracted from feed entry
    rating_field: str = "starRating"


@dataclass
class ReviewProducerConfig(ProducerConfig):
    review_feeds: list[ReviewFeedConfig] = field(default_factory=list)

    @classmethod
    def with_trustpilot(cls, brand_name: str, trustpilot_domain: str, **kwargs: object) -> "ReviewProducerConfig":
        """Convenience constructor for a Trustpilot-only config."""
        return cls(
            brand_name=brand_name,
            review_feeds=[
                ReviewFeedConfig(
                    platform=ReviewPlatform.TRUSTPILOT,
                    feed_url=f"https://www.trustpilot.com/review/{trustpilot_domain}?languages=all",
                )
            ],
            **kwargs,  # type: ignore[arg-type]
        )

    @classmethod
    def with_g2(cls, brand_name: str, g2_slug: str, **kwargs: object) -> "ReviewProducerConfig":
        return cls(
            brand_name=brand_name,
            review_feeds=[
                ReviewFeedConfig(
                    platform=ReviewPlatform.G2,
                    feed_url=f"https://www.g2.com/products/{g2_slug}/reviews.atom",
                )
            ],
            **kwargs,  # type: ignore[arg-type]
        )


class ReviewProducer(BaseProducer):
    """Fetches public review RSS feeds and emits BrandMentionEvents."""

    source_type = SourceType.REVIEW

    def __init__(self, config: ReviewProducerConfig, **kwargs: object) -> None:  # type: ignore[override]
        super().__init__(config, **kwargs)  # type: ignore[arg-type]
        self._review_config: ReviewProducerConfig = config

    def fetch_events(self) -> None:
        for feed_config in self._review_config.review_feeds:
            self._process_review_feed(feed_config)

    def _process_review_feed(self, feed_config: ReviewFeedConfig) -> None:
        log = logger.bind(platform=feed_config.platform, brand=self.config.brand_name)
        try:
            parsed = feedparser.parse(feed_config.feed_url)
        except Exception as exc:
            log.warning("Failed to fetch review feed", error=str(exc))
            return

        if not parsed.entries:
            log.info("No entries in review feed — platform may have removed public RSS")
            return

        for entry in parsed.entries:
            review = self._entry_to_review(entry, feed_config)
            if review is None:
                continue
            mention = review.to_brand_mention(self.config.brand_name)
            self.emit(mention)

    def _entry_to_review(
        self, entry: feedparser.FeedParserDict, feed_config: ReviewFeedConfig
    ) -> ReviewEvent | None:
        body: str = entry.get("summary", entry.get("description", "")).strip()
        if not body:
            return None

        # Extract rating: Trustpilot embeds it as `<rating>` in the feed
        rating: float | None = None
        raw_rating = (
            entry.get(feed_config.rating_field)
            or entry.get("rating")
            or self._extract_rating_from_text(body)
        )
        if raw_rating is not None:
            try:
                raw_float = float(str(raw_rating).split("/")[0].strip())
                rating = max(1.0, min(5.0, raw_float))
            except (ValueError, TypeError):
                pass

        published_at: datetime | None = None
        for date_field in ("published_parsed", "updated_parsed"):
            raw_date = entry.get(date_field)
            if raw_date:
                try:
                    published_at = datetime(*raw_date[:6], tzinfo=timezone.utc)
                    break
                except Exception:
                    continue

        review_id = entry.get("id") or entry.get("link") or entry.get("guid") or body[:64]

        return ReviewEvent(
            brand_id=self.config.brand_id,
            organization_id=self.config.organization_id,
            platform=feed_config.platform,
            review_id=str(review_id),
            title=entry.get("title") or None,
            body=body,
            rating=rating,
            source_url=entry.get("link") or feed_config.feed_url,
            published_at=int(published_at.timestamp() * 1000) if published_at else None,
        )

    @staticmethod
    def _extract_rating_from_text(text: str) -> str | None:
        """Last-resort: try to find a star rating in review text like '4/5' or '4 stars'."""
        m = re.search(r"\b([1-5])(?:\s*/\s*5|\s+star[s]?)\b", text, re.IGNORECASE)
        return m.group(1) if m else None
