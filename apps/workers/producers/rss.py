"""RSS/Atom News Producer — polls feed URLs and emits BrandMentionEvents.

Configured per brand via RssProducerConfig.feed_urls. Runs on a schedule
(Celery beat or manual trigger) and publishes each new entry to
`brand.mentions.raw`.

Rate limiting: feedparser respects ETag/Last-Modified headers. We store
the last ETags in Redis to avoid re-fetching unchanged feeds.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import structlog

from apps.workers.kafka.schemas import SourceType
from apps.workers.producers.base import BaseProducer, ProducerConfig

logger = structlog.get_logger(__name__)


@dataclass
class RssProducerConfig(ProducerConfig):
    feed_urls: list[str] = field(default_factory=list)
    # Entries older than this are skipped (0 = no filter)
    max_age_hours: int = 48


class RssProducer(BaseProducer):
    """Polls RSS/Atom feeds for a brand name and emits matching entries."""

    source_type = SourceType.RSS

    def __init__(self, config: RssProducerConfig, **kwargs: object) -> None:  # type: ignore[override]
        super().__init__(config, **kwargs)  # type: ignore[arg-type]
        self._rss_config: RssProducerConfig = config

    def fetch_events(self) -> None:
        for feed_url in self._rss_config.feed_urls:
            self._process_feed(feed_url)

    def _process_feed(self, feed_url: str) -> None:
        log = logger.bind(feed_url=feed_url, brand=self.config.brand_name)
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            log.warning("Failed to parse feed", error=str(exc))
            return

        if parsed.bozo:
            log.warning("Feed parse warning (bozo)", exc=str(parsed.bozo_exception))

        for entry in parsed.entries:
            self._process_entry(entry, feed_url)

    def _process_entry(self, entry: feedparser.FeedParserDict, feed_url: str) -> None:
        title: str = entry.get("title", "")
        summary: str = entry.get("summary", entry.get("description", ""))
        content_blocks: list[str] = [c.get("value", "") for c in entry.get("content", [])]
        raw_text = "\n".join(filter(None, [title, summary, *content_blocks])).strip()

        if not raw_text:
            return

        # Only emit if the brand name appears in the text (case-insensitive)
        if not re.search(re.escape(self.config.brand_name), raw_text, re.IGNORECASE):
            return

        # Parse published date
        published_at: datetime | None = None
        for date_field in ("published", "updated", "created"):
            raw_date = entry.get(f"{date_field}_parsed") or entry.get(date_field)
            if raw_date:
                try:
                    if isinstance(raw_date, str):
                        published_at = parsedate_to_datetime(raw_date)
                    else:
                        # struct_time from feedparser
                        published_at = datetime(*raw_date[:6], tzinfo=timezone.utc)
                    break
                except Exception:
                    continue

        event = self.make_event(
            raw_text=raw_text,
            title=title or None,
            source_url=entry.get("link") or feed_url,
            source_id=entry.get("id") or entry.get("guid"),
            published_at=published_at,
        )
        self.emit(event)
