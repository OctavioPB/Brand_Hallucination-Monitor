"""Deduplication Consumer — drops duplicate brand mention events.

Deduplication strategy: Redis SETEX on content_hash (SHA-256 of raw_text).
- TTL = 30 days (covers typical re-ingestion windows).
- On duplicate → message is committed and counted as `skipped` (not DLQ'd).
- On Redis failure → fail-open: message passes through with a WARNING log.
  (Prefer a duplicate in the pipeline over data loss.)

Why Redis SETEX over a Bloom filter:
- No false positives: every hash that Redis says "exists" actually does.
- 30-day window is manageable at 500 events/min: ~21.6M entries/month.
  At ~80 bytes/key → ~1.7 GB Redis memory. Acceptable for this scale.
- If memory becomes a constraint, swap to RedisBloom at Sprint 9.
"""
from __future__ import annotations

import structlog
from confluent_kafka import Message
from redis import Redis

from apps.api.config import get_settings
from apps.workers.consumers.base import BaseConsumer
from apps.workers.kafka.schemas import BrandMentionEvent
from apps.workers.kafka.topics import Topics

logger = structlog.get_logger(__name__)
settings = get_settings()

_DEDUP_TTL_SECONDS: int = 60 * 60 * 24 * 30  # 30 days
_REDIS_KEY_PREFIX: str = "dedup:mention:"


class DeduplicationConsumer(BaseConsumer):
    """Reads brand.mentions.raw, drops duplicates, forwards unique events to brand.mentions.enriched."""

    group_id = "hallucin8-dedup-consumer"
    input_topics = [Topics.BRAND_MENTIONS_RAW]

    def __init__(self, redis_client: Redis | None = None, **kwargs: object) -> None:  # type: ignore[override]
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._redis: Redis = redis_client or Redis.from_url(settings.redis_url, decode_responses=True)

    def process_message(self, event: BrandMentionEvent, raw_msg: Message) -> None:
        redis_key = f"{_REDIS_KEY_PREFIX}{event.content_hash}"

        try:
            # NX = only set if key does not exist
            is_new = self._redis.set(redis_key, "1", ex=_DEDUP_TTL_SECONDS, nx=True)
        except Exception as exc:
            # Redis unavailable — fail-open, pass the message through
            logger.warning(
                "Redis unavailable during dedup — passing message through",
                error=str(exc),
                content_hash=event.content_hash,
            )
            is_new = True

        if not is_new:
            logger.debug("Duplicate event dropped", content_hash=event.content_hash)
            self._skipped += 1
            return

        # Forward to enrichment topic
        self._producer.produce(
            topic=Topics.BRAND_MENTIONS_ENRICHED,
            value=event,
            key=event.brand_name,
        )
        self._processed += 1
