"""Abstract base class for all Kafka consumers in the ingestion pipeline.

Each consumer:
1. Reads a batch of messages from its input topic(s).
2. Processes each message — can filter (dedup), transform (enrich), or route.
3. Commits offsets only after all downstream writes succeed (at-least-once).
4. On unrecoverable failure, routes the raw message to the DLQ and commits.

All consumers are synchronous (run in Celery worker threads, not the async
FastAPI event loop).
"""
from __future__ import annotations

import abc
import json
from typing import Any

import structlog
from confluent_kafka import Consumer, Message

from apps.workers.kafka.client import ProducerClient, build_consumer, send_to_dlq
from apps.workers.kafka.schemas import BrandMentionEvent
from apps.workers.kafka.topics import Topics

logger = structlog.get_logger(__name__)

# How long to wait for a batch before returning (ms)
_POLL_TIMEOUT_MS: float = 1.0
# Batch size: how many messages to collect before processing
_BATCH_SIZE: int = 50


class BaseConsumer(abc.ABC):
    """Poll a Kafka topic, process messages, and commit offsets.

    Subclasses must implement `process_message()`.
    """

    group_id: str = "hallucin8-base-consumer"
    input_topics: list[str] = []

    def __init__(
        self,
        consumer: Consumer | None = None,
        producer_client: ProducerClient | None = None,
    ) -> None:
        self._consumer: Consumer = consumer or build_consumer(
            group_id=self.group_id, topics=self.input_topics
        )
        self._producer = producer_client or ProducerClient()
        self._processed = 0
        self._skipped = 0
        self._failed = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def run_once(self, max_messages: int = 500, timeout_s: float = 30.0) -> dict[str, int]:
        """Process up to `max_messages` and return. Suitable for Celery tasks."""
        log = logger.bind(consumer=self.__class__.__name__, group=self.group_id)
        count = 0
        import time
        deadline = time.monotonic() + timeout_s

        try:
            while count < max_messages and time.monotonic() < deadline:
                msg = self._consumer.poll(_POLL_TIMEOUT_MS)
                if msg is None:
                    break
                if msg.error():
                    if msg.error().code() == -191:  # PARTITION_EOF
                        break
                    log.error("Consumer poll error", error=str(msg.error()))
                    break
                self._handle_message(msg)
                count += 1
        finally:
            if count > 0:
                self._consumer.commit(asynchronous=False)
            log.info(
                "Consumer run finished",
                processed=self._processed,
                skipped=self._skipped,
                failed=self._failed,
            )
        return {"processed": self._processed, "skipped": self._skipped, "failed": self._failed}

    def close(self) -> None:
        self._consumer.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _handle_message(self, msg: Message) -> None:
        raw_value = msg.value()
        if raw_value is None:
            return
        try:
            data = json.loads(raw_value.decode())
            event = BrandMentionEvent.model_validate(data)
            self.process_message(event, msg)
        except Exception as exc:
            logger.error("Message processing failed — routing to DLQ", error=str(exc))
            send_to_dlq(self._producer, msg.topic(), raw_value, reason=str(exc))
            self._failed += 1

    @abc.abstractmethod
    def process_message(self, event: BrandMentionEvent, raw_msg: Message) -> None:
        """Process a single deserialized event. Called for every non-error message."""
