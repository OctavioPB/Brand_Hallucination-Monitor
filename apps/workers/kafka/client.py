"""Kafka producer and consumer factories using confluent-kafka.

Design notes:
- All Kafka I/O runs in Celery workers (sync context), never in FastAPI's async loop.
- The FastAPI mention endpoint uses ProducerClient via asyncio.run_in_executor.
- Schema Registry is optional: if SR_URL is blank, we serialize as plain JSON bytes.
  This lets unit tests run without a live Redpanda instance.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import structlog
from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer, AvroSerializer
from confluent_kafka.serialization import (
    MessageField,
    SerializationContext,
    StringDeserializer,
    StringSerializer,
)

from apps.api.config import get_settings
from apps.workers.kafka.schemas import BrandMentionEvent

logger = structlog.get_logger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Schema Registry (optional)
# ---------------------------------------------------------------------------
def get_schema_registry_client() -> SchemaRegistryClient | None:
    sr_url = getattr(settings, "schema_registry_url", "")
    if not sr_url:
        # Derive from Redpanda address: Redpanda SR runs on port 8081
        bootstrap = settings.kafka_bootstrap_servers.split(",")[0]
        host = bootstrap.split(":")[0]
        sr_url = f"http://{host}:8081"
    try:
        client = SchemaRegistryClient({"url": sr_url})
        client.get_subjects()  # probe connectivity
        return client
    except Exception as exc:
        logger.warning("Schema Registry unavailable — falling back to JSON serialization", error=str(exc))
        return None


# ---------------------------------------------------------------------------
# JSON fallback serializer/deserializer
# ---------------------------------------------------------------------------
def _json_serialize(obj: Any, ctx: SerializationContext | None = None) -> bytes:
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump()).encode()
    return json.dumps(obj).encode()


def _json_deserialize(data: bytes | None, ctx: SerializationContext | None = None) -> dict[str, Any] | None:
    if data is None:
        return None
    return json.loads(data.decode())


# ---------------------------------------------------------------------------
# Producer factory
# ---------------------------------------------------------------------------
def build_producer(extra_config: dict[str, Any] | None = None) -> Producer:
    config: dict[str, Any] = {
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "acks": "all",
        "retries": 5,
        "retry.backoff.ms": 500,
        "compression.type": "snappy",
        "linger.ms": 5,
        "batch.size": 65536,
    }
    if extra_config:
        config.update(extra_config)
    return Producer(config)


class ProducerClient:
    """Thread-safe wrapper around confluent Producer with delivery logging."""

    def __init__(self, producer: Producer | None = None) -> None:
        self._producer = producer or build_producer()

    def produce(self, topic: str, value: Any, key: str | None = None) -> None:
        serialized: bytes
        if isinstance(value, bytes):
            serialized = value
        elif hasattr(value, "model_dump"):
            serialized = json.dumps(value.model_dump(), default=str).encode()
        else:
            serialized = json.dumps(value, default=str).encode()

        self._producer.produce(
            topic=topic,
            value=serialized,
            key=key.encode() if key else None,
            on_delivery=self._delivery_report,
        )
        self._producer.poll(0)  # trigger callbacks without blocking

    def flush(self, timeout: float = 10.0) -> None:
        remaining = self._producer.flush(timeout=timeout)
        if remaining > 0:
            logger.warning("Producer flush timed out", remaining_messages=remaining)

    @staticmethod
    def _delivery_report(err: KafkaError | None, msg: Any) -> None:
        if err:
            logger.error(
                "Kafka delivery failed",
                topic=msg.topic(),
                partition=msg.partition(),
                error=str(err),
            )
        else:
            logger.debug(
                "Kafka delivery confirmed",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )


# ---------------------------------------------------------------------------
# Consumer factory
# ---------------------------------------------------------------------------
def build_consumer(
    group_id: str,
    topics: list[str],
    extra_config: dict[str, Any] | None = None,
) -> Consumer:
    config: dict[str, Any] = {
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,   # manual commit for at-least-once semantics
        "max.poll.interval.ms": 300000,
        "session.timeout.ms": 30000,
    }
    if extra_config:
        config.update(extra_config)
    consumer = Consumer(config)
    consumer.subscribe(topics)
    return consumer


# ---------------------------------------------------------------------------
# DLQ helper
# ---------------------------------------------------------------------------
def send_to_dlq(
    producer: ProducerClient,
    original_topic: str,
    raw_bytes: bytes,
    reason: str,
) -> None:
    from apps.workers.kafka.topics import Topics

    payload = {
        "original_topic": original_topic,
        "reason": reason,
        "raw_bytes_hex": raw_bytes.hex(),
    }
    producer.produce(Topics.MENTIONS_DLQ, value=payload)
    logger.warning("Message sent to DLQ", topic=original_topic, reason=reason)
