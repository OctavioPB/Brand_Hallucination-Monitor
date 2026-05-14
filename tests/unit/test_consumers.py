"""Unit tests: consumers with mocked Kafka and Redis clients."""
import json
from unittest.mock import MagicMock, patch

import pytest

from apps.workers.kafka.schemas import BrandMentionEvent, SourceType
from apps.workers.kafka.topics import Topics


def _make_event(**kwargs) -> BrandMentionEvent:
    defaults = dict(brand_name="AcmeCorp", raw_text="AcmeCorp test mention", source_type=SourceType.MANUAL)
    defaults.update(kwargs)
    return BrandMentionEvent(**defaults)


def _make_raw_msg(event: BrandMentionEvent) -> MagicMock:
    msg = MagicMock()
    msg.value.return_value = json.dumps(event.model_dump()).encode()
    msg.topic.return_value = Topics.BRAND_MENTIONS_RAW
    msg.error.return_value = None
    msg.offset.return_value = 0
    msg.partition.return_value = 0
    return msg


class FakeProducerClient:
    def __init__(self):
        self.produced: list[dict] = []

    def produce(self, topic, value, key=None):
        self.produced.append({"topic": topic, "value": value, "key": key})

    def flush(self, timeout=10.0):
        pass


# ---------------------------------------------------------------------------
# DeduplicationConsumer
# ---------------------------------------------------------------------------
class TestDeduplicationConsumer:
    def _make_consumer(self, redis_mock=None):
        from apps.workers.consumers.deduplication import DeduplicationConsumer
        mock_kafka_consumer = MagicMock()
        producer = FakeProducerClient()
        redis = redis_mock or MagicMock()
        return DeduplicationConsumer(
            consumer=mock_kafka_consumer,
            producer_client=producer,
            redis_client=redis,
        ), producer, redis

    def test_new_message_forwarded_to_enriched_topic(self):
        consumer, producer, redis = self._make_consumer()
        redis.set.return_value = True  # NX succeeded → new message
        event = _make_event()
        consumer.process_message(event, _make_raw_msg(event))
        assert len(producer.produced) == 1
        assert producer.produced[0]["topic"] == Topics.BRAND_MENTIONS_ENRICHED

    def test_duplicate_message_dropped(self):
        consumer, producer, redis = self._make_consumer()
        redis.set.return_value = None  # NX failed → duplicate
        event = _make_event()
        consumer.process_message(event, _make_raw_msg(event))
        assert len(producer.produced) == 0
        assert consumer._skipped == 1

    def test_redis_failure_passes_message_through(self):
        consumer, producer, redis = self._make_consumer()
        redis.set.side_effect = Exception("Redis connection refused")
        event = _make_event()
        consumer.process_message(event, _make_raw_msg(event))
        # Fail-open: message forwarded despite Redis error
        assert len(producer.produced) == 1

    def test_dedup_key_uses_content_hash(self):
        consumer, producer, redis = self._make_consumer()
        redis.set.return_value = True
        event = _make_event(raw_text="unique content xyz")
        consumer.process_message(event, _make_raw_msg(event))
        # Verify the key contains the content hash
        call_args = redis.set.call_args
        key = call_args[0][0]
        assert event.content_hash in key


# ---------------------------------------------------------------------------
# RoutingConsumer
# ---------------------------------------------------------------------------
class TestRoutingConsumer:
    def _make_consumer(self):
        from apps.workers.consumers.routing import RoutingConsumer
        mock_kafka_consumer = MagicMock()
        producer = FakeProducerClient()
        consumer = RoutingConsumer(consumer=mock_kafka_consumer, producer_client=producer)
        consumer._db_conn = None  # disable DB persistence in unit tests
        return consumer, producer

    def test_enriched_event_routed_to_embeddings(self):
        consumer, producer = self._make_consumer()
        event = _make_event(brand_id="uuid-123", organization_id="org-1")
        consumer.process_message(event, _make_raw_msg(event))
        topics = [p["topic"] for p in producer.produced]
        assert Topics.EMBEDDINGS_PENDING in topics

    def test_unenriched_event_skipped(self):
        consumer, producer = self._make_consumer()
        event = _make_event(brand_id="")  # not yet enriched
        consumer.process_message(event, _make_raw_msg(event))
        assert len(producer.produced) == 0
        assert consumer._skipped == 1

    def test_hallucination_keyword_triggers_alert(self):
        consumer, producer = self._make_consumer()
        event = _make_event(
            brand_id="uuid-123",
            organization_id="org-1",
            raw_text="This is totally incorrect about AcmeCorp",
        )
        consumer.process_message(event, _make_raw_msg(event))
        topics = [p["topic"] for p in producer.produced]
        assert Topics.HALLUCINATION_ALERTS in topics

    def test_normal_content_no_alert(self):
        consumer, producer = self._make_consumer()
        event = _make_event(
            brand_id="uuid-123",
            organization_id="org-1",
            raw_text="AcmeCorp is a great company with excellent support",
        )
        consumer.process_message(event, _make_raw_msg(event))
        topics = [p["topic"] for p in producer.produced]
        assert Topics.HALLUCINATION_ALERTS not in topics
        assert Topics.EMBEDDINGS_PENDING in topics


# ---------------------------------------------------------------------------
# Topics constants
# ---------------------------------------------------------------------------
class TestTopics:
    def test_topic_names_stable(self):
        assert Topics.BRAND_MENTIONS_RAW == "brand.mentions.raw"
        assert Topics.BRAND_MENTIONS_ENRICHED == "brand.mentions.enriched"
        assert Topics.EMBEDDINGS_PENDING == "embeddings.pending"
        assert Topics.HALLUCINATION_ALERTS == "hallucination.alerts"
        assert Topics.MENTIONS_DLQ == "mentions.dlq"

    def test_topics_frozen(self):
        from dataclasses import FrozenInstanceError
        with pytest.raises((FrozenInstanceError, TypeError)):
            Topics.BRAND_MENTIONS_RAW = "hacked"  # type: ignore[misc]
