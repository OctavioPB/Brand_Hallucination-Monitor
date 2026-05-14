"""Kafka topic name constants — single source of truth for the whole project."""
from dataclasses import dataclass


@dataclass(frozen=True)
class _Topics:
    BRAND_MENTIONS_RAW: str = "brand.mentions.raw"
    BRAND_MENTIONS_ENRICHED: str = "brand.mentions.enriched"
    COMPETITOR_MENTIONS_RAW: str = "competitor.mentions.raw"
    EMBEDDINGS_PENDING: str = "embeddings.pending"
    HALLUCINATION_ALERTS: str = "hallucination.alerts"
    MENTIONS_DLQ: str = "mentions.dlq"


Topics = _Topics()
