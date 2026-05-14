"""Integration tests: end-to-end pipeline (producer → consumer chain).

These tests use in-process mocks and verify that 100+ mentions flow
correctly through the full pipeline:
  RssProducer → DeduplicationConsumer → RoutingConsumer

No live Kafka/Redis/DB required — all external systems are mocked.

Definition of Done from PLAN.md:
> 100+ test brand mentions flow end-to-end from producer → Kafka → consumer
> in an integration test.
"""
import hashlib
import json
import random
import string
from typing import Any
from unittest.mock import MagicMock

import pytest

from apps.workers.kafka.schemas import BrandMentionEvent, SourceType
from apps.workers.kafka.topics import Topics


def _random_text(n_words: int = 20) -> str:
    words = ["AcmeCorp"] + [
        "".join(random.choices(string.ascii_lowercase, k=random.randint(3, 10)))
        for _ in range(n_words - 1)
    ]
    random.shuffle(words)
    return " ".join(words)


class InMemoryBroker:
    """Minimal in-process Kafka broker for integration testing."""

    def __init__(self):
        self._topics: dict[str, list[bytes]] = {}

    def produce(self, topic: str, value: Any, key: str | None = None) -> None:
        if topic not in self._topics:
            self._topics[topic] = []
        if isinstance(value, bytes):
            self._topics[topic].append(value)
        elif hasattr(value, "model_dump"):
            self._topics[topic].append(json.dumps(value.model_dump(), default=str).encode())
        else:
            self._topics[topic].append(json.dumps(value, default=str).encode())

    def flush(self, timeout: float = 10.0) -> None:
        pass

    def messages(self, topic: str) -> list[bytes]:
        return self._topics.get(topic, [])

    def count(self, topic: str) -> int:
        return len(self.messages(topic))


class InMemoryRedis:
    """Minimal Redis mock supporting SETEX with NX."""

    def __init__(self):
        self._store: dict[str, str] = {}

    def set(self, key: str, value: str, ex: int | None = None, nx: bool = False) -> bool | None:
        if nx:
            if key in self._store:
                return None  # NX failed → key exists
            self._store[key] = value
            return True
        self._store[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self._store.get(key)


class TestEndToEndPipeline:
    N_MENTIONS = 120  # > 100 as required by PLAN.md DoD

    def _build_events(self, n: int) -> list[BrandMentionEvent]:
        return [
            BrandMentionEvent.from_raw_text(
                brand_name="AcmeCorp",
                raw_text=_random_text(20),
                source_type=SourceType.RSS,
                source_url=f"https://news.example.com/article-{i}",
            )
            for i in range(n)
        ]

    def test_100_unique_mentions_all_reach_embeddings_pending(self):
        """100+ unique events should all be routed to embeddings.pending."""
        broker = InMemoryBroker()
        redis = InMemoryRedis()

        # 1. Simulate producer writing N events to brand.mentions.raw
        events = self._build_events(self.N_MENTIONS)
        for event in events:
            broker.produce(Topics.BRAND_MENTIONS_RAW, event)

        raw_count = broker.count(Topics.BRAND_MENTIONS_RAW)
        assert raw_count == self.N_MENTIONS

        # 2. Run DeduplicationConsumer in-process
        from apps.workers.consumers.deduplication import DeduplicationConsumer

        dedup = DeduplicationConsumer(
            consumer=MagicMock(),
            producer_client=broker,
            redis_client=redis,
        )
        for event in events:
            dedup.process_message(event, MagicMock(topic=lambda: Topics.BRAND_MENTIONS_RAW, value=lambda: None))

        enriched_count = broker.count(Topics.BRAND_MENTIONS_ENRICHED)
        assert enriched_count == self.N_MENTIONS, (
            f"Expected {self.N_MENTIONS} enriched events, got {enriched_count}"
        )

        # 3. Run RoutingConsumer in-process
        from apps.workers.consumers.routing import RoutingConsumer

        router = RoutingConsumer(
            consumer=MagicMock(),
            producer_client=broker,
        )
        router._db_conn = None  # disable DB writes

        for event in events:
            enriched = event.model_copy(update={"brand_id": "uuid-001", "organization_id": "org-001"})
            router.process_message(enriched, MagicMock(topic=lambda: Topics.BRAND_MENTIONS_ENRICHED, value=lambda: None, offset=lambda: 0, partition=lambda: 0))

        pending_count = broker.count(Topics.EMBEDDINGS_PENDING)
        assert pending_count == self.N_MENTIONS, (
            f"Expected {self.N_MENTIONS} in embeddings.pending, got {pending_count}"
        )

    def test_duplicate_mentions_deduplicated(self):
        """50 events where 25 are duplicates → only 25 unique events forwarded."""
        broker = InMemoryBroker()
        redis = InMemoryRedis()

        unique_events = self._build_events(25)
        duplicate_events = unique_events * 2  # 50 total, 25 unique

        from apps.workers.consumers.deduplication import DeduplicationConsumer

        dedup = DeduplicationConsumer(
            consumer=MagicMock(),
            producer_client=broker,
            redis_client=redis,
        )

        for event in duplicate_events:
            dedup.process_message(event, MagicMock(topic=lambda: Topics.BRAND_MENTIONS_RAW, value=lambda: None))

        enriched_count = broker.count(Topics.BRAND_MENTIONS_ENRICHED)
        assert enriched_count == 25
        assert dedup._skipped == 25
        assert dedup._processed == 25

    def test_zero_data_loss_on_redis_failure(self):
        """If Redis is down, all messages pass through (fail-open dedup)."""
        broker = InMemoryBroker()

        failing_redis = MagicMock()
        failing_redis.set.side_effect = Exception("Connection refused")

        events = self._build_events(10)

        from apps.workers.consumers.deduplication import DeduplicationConsumer

        dedup = DeduplicationConsumer(
            consumer=MagicMock(),
            producer_client=broker,
            redis_client=failing_redis,
        )
        for event in events:
            dedup.process_message(event, MagicMock(topic=lambda: Topics.BRAND_MENTIONS_RAW, value=lambda: None))

        # Fail-open: all 10 messages forwarded despite Redis failure
        assert broker.count(Topics.BRAND_MENTIONS_ENRICHED) == 10

    def test_unenriched_events_not_sent_to_embeddings(self):
        """Events without brand_id must be skipped by the routing consumer."""
        broker = InMemoryBroker()

        from apps.workers.consumers.routing import RoutingConsumer

        router = RoutingConsumer(consumer=MagicMock(), producer_client=broker)
        router._db_conn = None

        events = self._build_events(5)
        for event in events:
            router.process_message(event, MagicMock(topic=lambda: Topics.BRAND_MENTIONS_ENRICHED, value=lambda: None, offset=lambda: 0, partition=lambda: 0))

        assert broker.count(Topics.EMBEDDINGS_PENDING) == 0
        assert router._skipped == 5

    def test_dlq_receives_invalid_messages(self):
        """A malformed message should be sent to the DLQ."""
        broker = InMemoryBroker()

        class FailingDedup:
            pass

        # Test the base consumer's _handle_message DLQ path
        from apps.workers.consumers.base import BaseConsumer
        from apps.workers.kafka.client import ProducerClient

        class ThrowingConsumer(BaseConsumer):
            group_id = "test-group"
            input_topics = [Topics.BRAND_MENTIONS_RAW]

            def process_message(self, event, raw_msg):
                raise ValueError("intentional failure")

        thrower = ThrowingConsumer(consumer=MagicMock(), producer_client=broker)
        bad_msg = MagicMock()
        bad_msg.value.return_value = json.dumps(
            {"brand_name": "X", "raw_text": "text", "source_type": "manual",
             "content_hash": "abc", "event_id": "e1", "ingested_at": 0, "schema_version": "1.0.0"}
        ).encode()
        bad_msg.topic.return_value = Topics.BRAND_MENTIONS_RAW
        bad_msg.error.return_value = None

        thrower._handle_message(bad_msg)

        dlq_count = broker.count(Topics.MENTIONS_DLQ)
        assert dlq_count == 1
