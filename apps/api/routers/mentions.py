"""POST /api/v1/mentions — manual brand mention injection endpoint.

Accepts a single brand mention payload, publishes it to `brand.mentions.raw`,
and returns 202 Accepted. The ingestion pipeline (dedup → enrich → route)
processes the event asynchronously.

Kafka I/O runs in a thread pool executor to avoid blocking FastAPI's event loop.
The ProducerClient is reused across requests via a module-level singleton.
"""
import asyncio
from functools import lru_cache

import structlog
from fastapi import APIRouter, HTTPException, status

from apps.api.models.mention import MentionCreate, MentionResponse
from apps.workers.kafka.client import ProducerClient
from apps.workers.kafka.schemas import BrandMentionEvent
from apps.workers.kafka.topics import Topics

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["mentions"])


@lru_cache(maxsize=1)
def _get_producer() -> ProducerClient:
    return ProducerClient()


def _publish_sync(event: BrandMentionEvent) -> None:
    """Runs in thread pool — never call directly from async context."""
    producer = _get_producer()
    producer.produce(topic=Topics.BRAND_MENTIONS_RAW, value=event, key=event.brand_name)
    producer.flush(timeout=5.0)


@router.post(
    "/mentions",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MentionResponse,
    summary="Inject a brand mention manually",
    description=(
        "Accepts a brand mention and publishes it to `brand.mentions.raw`. "
        "Use this endpoint for webhooks, manual testing, or integrations that "
        "don't fit the RSS/Reddit/Review producer pipeline."
    ),
)
async def create_mention(payload: MentionCreate) -> MentionResponse:
    event = BrandMentionEvent.from_raw_text(
        brand_name=payload.brand_name,
        raw_text=payload.raw_text,
        source_type=payload.source_type,
        source_url=payload.source_url,
        source_id=payload.source_id,
        title=payload.title,
        published_at=payload.published_at,
    )

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _publish_sync, event)
    except Exception as exc:
        logger.error("Failed to publish mention to Kafka", error=str(exc), event_id=event.event_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Message broker unavailable. Retry in a few seconds.",
        ) from exc

    logger.info(
        "Mention queued",
        event_id=event.event_id,
        brand_name=event.brand_name,
        source_type=event.source_type,
        content_hash=event.content_hash,
    )

    return MentionResponse(
        event_id=event.event_id,
        brand_name=event.brand_name,
        content_hash=event.content_hash,
        source_type=event.source_type.value,
    )
