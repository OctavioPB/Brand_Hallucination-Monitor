"""Routing Consumer — inspects enriched events and routes to final topic(s).

Reads from brand.mentions.enriched (after enrichment pass, i.e. brand_id is set).
Routes each event to:
- embeddings.pending  → always (for vector ETL in Sprint 3)
- hallucination.alerts → if event text triggers a hallucination heuristic
  (full ML classifier in Sprint 5; here we use a keyword-based placeholder)

The consumer also persists each mention to the `brand_mentions` PostgreSQL
table for audit trail and retry-ability.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import structlog
from confluent_kafka import Message

from apps.workers.consumers.base import BaseConsumer
from apps.workers.kafka.schemas import BrandMentionEvent
from apps.workers.kafka.topics import Topics

logger = structlog.get_logger(__name__)

# Simple keyword heuristic for Sprint 2 — replaced by ML classifier in Sprint 5
_HALLUCINATION_KEYWORDS = [
    "false", "incorrect", "wrong", "lie", "fake", "doesn't exist",
    "not real", "made up", "confusing", "mistaken", "actually",
]


class RoutingConsumer(BaseConsumer):
    """Routes enriched mentions to embeddings.pending and optionally hallucination.alerts."""

    group_id = "hallucin8-routing-consumer"
    input_topics = [Topics.BRAND_MENTIONS_ENRICHED]

    def __init__(self, **kwargs: object) -> None:  # type: ignore[override]
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._db_conn = self._build_db_connection()

    def _build_db_connection(self) -> object | None:
        from apps.api.config import get_settings
        settings = get_settings()
        try:
            import psycopg2
            return psycopg2.connect(settings.database_url_sync)
        except Exception as exc:
            logger.warning("Routing consumer: DB unavailable — mentions not persisted", error=str(exc))
            return None

    def process_message(self, event: BrandMentionEvent, raw_msg: Message) -> None:
        if not event.brand_id:
            # Not yet enriched — skip, enrichment consumer will re-publish
            self._skipped += 1
            return

        # 1. Always route to embeddings pipeline
        self._producer.produce(
            topic=Topics.EMBEDDINGS_PENDING,
            value=event,
            key=event.brand_id,
        )

        # 2. Heuristic hallucination flag (Sprint 5 replaces this)
        if self._looks_like_hallucination(event.raw_text):
            alert_payload = {
                "event_id": event.event_id,
                "brand_id": event.brand_id,
                "organization_id": event.organization_id,
                "severity": "LOW",
                "alert_type": "potential_hallucination_keyword",
                "source_url": event.source_url,
                "snippet": event.raw_text[:500],
            }
            self._producer.produce(
                topic=Topics.HALLUCINATION_ALERTS,
                value=alert_payload,
                key=event.brand_id,
            )

        # 3. Persist to brand_mentions table
        self._persist_mention(event, raw_msg)
        self._processed += 1

    def _looks_like_hallucination(self, text: str) -> bool:
        lower = text.lower()
        return any(kw in lower for kw in _HALLUCINATION_KEYWORDS)

    def _persist_mention(self, event: BrandMentionEvent, raw_msg: Message) -> None:
        if self._db_conn is None:
            return
        try:
            published_dt: datetime | None = None
            if event.published_at:
                published_dt = datetime.fromtimestamp(event.published_at / 1000, tz=timezone.utc)

            with self._db_conn.cursor() as cur:  # type: ignore[union-attr]
                cur.execute(
                    """
                    INSERT INTO brand_mentions (
                        id, brand_id, organization_id, source_type, source_url,
                        source_id, title, raw_text, content_hash, metadata,
                        kafka_offset, kafka_partition, processed, embedding_queued,
                        published_at
                    ) VALUES (
                        %s, %s::uuid, %s, %s, %s,
                        %s, %s, %s, %s, %s::jsonb,
                        %s, %s, false, true,
                        %s
                    )
                    ON CONFLICT (content_hash) DO NOTHING
                    """,
                    (
                        str(uuid.uuid4()),
                        event.brand_id,
                        event.organization_id,
                        event.source_type.value,
                        event.source_url,
                        event.source_id,
                        event.title,
                        event.raw_text,
                        event.content_hash,
                        json.dumps({"event_id": event.event_id}),
                        raw_msg.offset(),
                        raw_msg.partition(),
                        published_dt,
                    ),
                )
                self._db_conn.commit()  # type: ignore[union-attr]
        except Exception as exc:
            logger.error("Failed to persist mention to DB", error=str(exc))
            try:
                self._db_conn.rollback()  # type: ignore[union-attr]
            except Exception:
                pass

    def __del__(self) -> None:
        if self._db_conn:
            try:
                self._db_conn.close()  # type: ignore[union-attr]
            except Exception:
                pass
