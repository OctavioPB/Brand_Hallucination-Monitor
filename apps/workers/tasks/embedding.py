"""Embedding generation tasks — Sprint 3 implementation."""
import structlog

from apps.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="embedding.generate",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_embedding(self, brand_id: str, text: str, source_hash: str) -> dict[str, str]:
    """Queue an embedding generation job for a single text chunk.

    Full implementation in Sprint 3 — enqueues to Celery, calls OpenAI,
    stores in Qdrant and PostgreSQL.
    """
    logger.info("Embedding task received (stub)", brand_id=brand_id, hash=source_hash)
    # TODO Sprint 3: call OpenAI, store result in Qdrant + DB
    return {"status": "stub", "brand_id": brand_id, "hash": source_hash}
