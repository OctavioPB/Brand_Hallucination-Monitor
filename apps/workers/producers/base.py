"""Abstract base class for all ingestion producers."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

from apps.workers.kafka.client import ProducerClient, send_to_dlq
from apps.workers.kafka.schemas import BrandMentionEvent, SourceType
from apps.workers.kafka.topics import Topics

logger = structlog.get_logger(__name__)


@dataclass
class ProducerConfig:
    """Per-brand configuration injected into every producer."""

    brand_name: str
    brand_id: str = ""
    organization_id: str = ""
    # Additional producer-specific fields are added in subclass configs.
    extra: dict[str, object] = field(default_factory=dict)


class BaseProducer(abc.ABC):
    """Pull data from a source, emit BrandMentionEvents to Kafka.

    Subclasses override `fetch_events()` and call `emit()` for each event.
    The base class handles:
    - Delivery to `brand.mentions.raw`
    - DLQ routing on serialization failure
    - Metrics logging (events_emitted, events_failed)
    """

    source_type: SourceType = SourceType.UNKNOWN  # override in subclass

    def __init__(self, config: ProducerConfig, producer_client: ProducerClient | None = None) -> None:
        self.config = config
        self._client = producer_client or ProducerClient()
        self._emitted: int = 0
        self._failed: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def run(self) -> dict[str, int]:
        """Fetch and emit all events. Returns stats dict."""
        log = logger.bind(producer=self.__class__.__name__, brand=self.config.brand_name)
        log.info("Producer run started")
        try:
            self.fetch_events()
        except Exception as exc:
            log.error("Producer run failed", error=str(exc))
            raise
        finally:
            self._client.flush()
            log.info(
                "Producer run finished",
                emitted=self._emitted,
                failed=self._failed,
            )
        return {"emitted": self._emitted, "failed": self._failed}

    @abc.abstractmethod
    def fetch_events(self) -> None:
        """Fetch data from the source and call `self.emit()` for each item."""

    # ------------------------------------------------------------------
    # Protected helpers
    # ------------------------------------------------------------------
    def emit(self, event: BrandMentionEvent) -> None:
        """Publish a single event to brand.mentions.raw."""
        try:
            self._client.produce(
                topic=Topics.BRAND_MENTIONS_RAW,
                value=event,
                key=event.brand_name,
            )
            self._emitted += 1
        except Exception as exc:
            logger.error("Failed to emit event", error=str(exc), event_id=event.event_id)
            self._failed += 1

    def make_event(
        self,
        *,
        raw_text: str,
        source_url: str | None = None,
        source_id: str | None = None,
        title: str | None = None,
        published_at: datetime | None = None,
    ) -> BrandMentionEvent:
        """Convenience builder that fills in brand fields from config."""
        return BrandMentionEvent.from_raw_text(
            brand_name=self.config.brand_name,
            raw_text=raw_text,
            source_type=self.source_type,
            source_url=source_url,
            source_id=source_id,
            title=title,
            published_at=published_at,
        )
