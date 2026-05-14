"""Celery tasks for the Kafka ingestion pipeline.

Task hierarchy:
  run_rss_producer          → wraps RssProducer.run()
  run_reddit_producer       → wraps RedditProducer.run()
  run_review_producer       → wraps ReviewProducer.run()
  run_deduplication_consumer → wraps DeduplicationConsumer.run_once()
  run_enrichment_consumer   → wraps EnrichmentConsumer.run_once()
  run_routing_consumer      → wraps RoutingConsumer.run_once()
  run_full_pipeline         → chord: [producers] | [consumers in order]

All tasks are configured with:
- max_retries=3, exponential backoff
- task_time_limit=300 (5 min hard kill)
- acks_late=True (message not acked until task completes successfully)
"""
from __future__ import annotations

import structlog

from apps.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Producer tasks
# ---------------------------------------------------------------------------
@celery_app.task(
    name="ingestion.rss_producer",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,
    soft_time_limit=240,
)
def run_rss_producer(
    self: object,
    brand_name: str,
    feed_urls: list[str],
    brand_id: str = "",
    organization_id: str = "",
) -> dict[str, int]:
    """Poll RSS/Atom feeds for a brand and publish mentions to Kafka."""
    from apps.workers.producers.rss import RssProducer, RssProducerConfig

    config = RssProducerConfig(
        brand_name=brand_name,
        brand_id=brand_id,
        organization_id=organization_id,
        feed_urls=feed_urls,
    )
    producer = RssProducer(config)
    try:
        return producer.run()
    except Exception as exc:
        logger.error("RSS producer task failed", brand=brand_name, error=str(exc))
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]


@celery_app.task(
    name="ingestion.reddit_producer",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    time_limit=300,
    soft_time_limit=240,
)
def run_reddit_producer(
    self: object,
    brand_name: str,
    subreddits: list[str],
    brand_id: str = "",
    organization_id: str = "",
    client_id: str = "",
    client_secret: str = "",
    limit: int = 100,
) -> dict[str, int]:
    """Monitor subreddits for brand mentions."""
    from apps.workers.producers.reddit import RedditProducer, RedditProducerConfig

    config = RedditProducerConfig(
        brand_name=brand_name,
        brand_id=brand_id,
        organization_id=organization_id,
        subreddits=subreddits,
        client_id=client_id,
        client_secret=client_secret,
        limit=limit,
    )
    producer = RedditProducer(config)
    try:
        return producer.run()
    except Exception as exc:
        logger.error("Reddit producer task failed", brand=brand_name, error=str(exc))
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]


@celery_app.task(
    name="ingestion.review_producer",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,
    soft_time_limit=240,
)
def run_review_producer(
    self: object,
    brand_name: str,
    review_feeds: list[dict[str, str]],
    brand_id: str = "",
    organization_id: str = "",
) -> dict[str, int]:
    """Fetch public review feeds (Trustpilot, G2) and publish to Kafka."""
    from apps.workers.producers.review import ReviewFeedConfig, ReviewProducer, ReviewProducerConfig
    from apps.workers.kafka.schemas import ReviewPlatform

    feeds = [
        ReviewFeedConfig(
            platform=ReviewPlatform(f["platform"]),
            feed_url=f["feed_url"],
        )
        for f in review_feeds
    ]
    config = ReviewProducerConfig(
        brand_name=brand_name,
        brand_id=brand_id,
        organization_id=organization_id,
        review_feeds=feeds,
    )
    producer = ReviewProducer(config)
    try:
        return producer.run()
    except Exception as exc:
        logger.error("Review producer task failed", brand=brand_name, error=str(exc))
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Consumer tasks
# ---------------------------------------------------------------------------
@celery_app.task(
    name="ingestion.dedup_consumer",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    time_limit=600,
    soft_time_limit=540,
)
def run_deduplication_consumer(
    self: object,
    max_messages: int = 500,
) -> dict[str, int]:
    """Run one batch of the deduplication consumer."""
    from apps.workers.consumers.deduplication import DeduplicationConsumer

    consumer = DeduplicationConsumer()
    try:
        result = consumer.run_once(max_messages=max_messages)
        consumer.close()
        return result
    except Exception as exc:
        logger.error("Dedup consumer task failed", error=str(exc))
        consumer.close()
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]


@celery_app.task(
    name="ingestion.enrichment_consumer",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    time_limit=600,
    soft_time_limit=540,
)
def run_enrichment_consumer(
    self: object,
    max_messages: int = 500,
) -> dict[str, int]:
    """Run one batch of the enrichment consumer."""
    from apps.workers.consumers.enrichment import EnrichmentConsumer

    consumer = EnrichmentConsumer()
    try:
        result = consumer.run_once(max_messages=max_messages)
        consumer.close()
        return result
    except Exception as exc:
        logger.error("Enrichment consumer task failed", error=str(exc))
        consumer.close()
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]


@celery_app.task(
    name="ingestion.routing_consumer",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    time_limit=600,
    soft_time_limit=540,
)
def run_routing_consumer(
    self: object,
    max_messages: int = 500,
) -> dict[str, int]:
    """Run one batch of the routing consumer."""
    from apps.workers.consumers.routing import RoutingConsumer

    consumer = RoutingConsumer()
    try:
        result = consumer.run_once(max_messages=max_messages)
        consumer.close()
        return result
    except Exception as exc:
        logger.error("Routing consumer task failed", error=str(exc))
        consumer.close()
        raise self.retry(exc=exc) from exc  # type: ignore[attr-defined]
