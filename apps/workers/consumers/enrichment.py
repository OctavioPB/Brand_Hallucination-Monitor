"""Enrichment Consumer — adds brand_id, organization_id, and competitor flags.

Reads from brand.mentions.enriched (post-dedup), writes back to the same
topic (or alternatively to a dedicated enriched-v2 topic in future sprints).

Brand lookup strategy:
1. Check Redis cache (key: `brand:name:{normalized_name}`, TTL 5 min).
2. On miss → query PostgreSQL `brands` table, populate cache.
3. If brand not found → route to DLQ with reason `brand_not_found`.

Why sync DB access: this consumer runs in a Celery worker thread, not in
FastAPI's async loop. Using `psycopg2` directly is correct here.
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache

import structlog
from confluent_kafka import Message
from redis import Redis

from apps.api.config import get_settings
from apps.workers.consumers.base import BaseConsumer
from apps.workers.kafka.schemas import BrandMentionEvent
from apps.workers.kafka.topics import Topics

logger = structlog.get_logger(__name__)
settings = get_settings()

_BRAND_CACHE_TTL: int = 300  # 5 minutes
_BRAND_CACHE_PREFIX: str = "brand:name:"


class EnrichmentConsumer(BaseConsumer):
    """Reads deduplicated events, enriches with brand/org IDs, re-publishes."""

    group_id = "hallucin8-enrichment-consumer"
    input_topics = [Topics.BRAND_MENTIONS_ENRICHED]

    def __init__(self, redis_client: Redis | None = None, **kwargs: object) -> None:  # type: ignore[override]
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._redis: Redis = redis_client or Redis.from_url(settings.redis_url, decode_responses=True)
        self._db_conn = self._build_db_connection()

    def _build_db_connection(self) -> object | None:
        try:
            import psycopg2
            return psycopg2.connect(settings.database_url_sync)
        except Exception as exc:
            logger.warning("Cannot connect to DB for enrichment — brand lookup disabled", error=str(exc))
            return None

    def process_message(self, event: BrandMentionEvent, raw_msg: Message) -> None:
        brand_info = self._lookup_brand(event.brand_name)

        if brand_info is None:
            from apps.workers.kafka.client import send_to_dlq
            send_to_dlq(
                self._producer,
                original_topic=raw_msg.topic(),
                raw_bytes=raw_msg.value(),
                reason=f"brand_not_found:{event.brand_name}",
            )
            self._failed += 1
            return

        enriched = event.model_copy(
            update={
                "brand_id": brand_info["brand_id"],
                "organization_id": brand_info["organization_id"],
            }
        )

        # Publish enriched event — routing consumer picks this up
        self._producer.produce(
            topic=Topics.BRAND_MENTIONS_ENRICHED,
            value=enriched,
            key=enriched.brand_id,
        )
        self._processed += 1

    def _lookup_brand(self, brand_name: str) -> dict[str, str] | None:
        """Returns {'brand_id': ..., 'organization_id': ...} or None."""
        cache_key = f"{_BRAND_CACHE_PREFIX}{brand_name.lower().strip()}"

        # 1. Redis cache
        try:
            cached = self._redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as exc:
            logger.warning("Redis cache read failed", error=str(exc))

        # 2. PostgreSQL
        if self._db_conn is None:
            return None
        try:
            with self._db_conn.cursor() as cur:  # type: ignore[union-attr]
                cur.execute(
                    "SELECT id::text, organization_id FROM brands WHERE LOWER(name) = LOWER(%s) LIMIT 1",
                    (brand_name,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                result = {"brand_id": row[0], "organization_id": row[1]}
                # Populate cache
                try:
                    self._redis.set(cache_key, json.dumps(result), ex=_BRAND_CACHE_TTL)
                except Exception:
                    pass
                return result
        except Exception as exc:
            logger.error("DB brand lookup failed", error=str(exc), brand_name=brand_name)
            return None

    def __del__(self) -> None:
        if self._db_conn:
            try:
                self._db_conn.close()  # type: ignore[union-attr]
            except Exception:
                pass
