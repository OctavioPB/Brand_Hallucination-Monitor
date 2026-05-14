"""Embedding Celery tasks — Sprint 3.

These tasks are triggered by the routing consumer when a brand mention is
routed to the embeddings.pending Kafka topic. They provide a Celery-native
path for embedding single events in near-real-time (low latency), complementing
the hourly Airflow DAG batch path (high throughput).

Both paths write to the same Qdrant collections and sps_scores table;
the EmbeddingService Redis cache ensures no duplicate OpenAI API calls.
"""
import logging
import os

import structlog

from apps.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)

_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
_OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
_DB_URL_SYNC = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://hallucin8:hallucin8@localhost:5432/hallucin8",
)


def _get_services() -> tuple:
    """Lazy-initialize EmbeddingService and QdrantStore per Celery worker.

    Returns (EmbeddingService, QdrantStore) — created once per worker process
    via task-level caching (Celery re-uses task instances).
    """
    import redis as redis_lib

    from ml.embeddings.qdrant_store import QdrantStore
    from ml.embeddings.service import EmbeddingService

    redis_client = redis_lib.from_url(_REDIS_URL, decode_responses=True)
    svc = EmbeddingService(
        api_key=_OPENAI_API_KEY,
        redis_client=redis_client,
        db_url=_DB_URL_SYNC,
    )
    qdrant = QdrantStore(url=_QDRANT_URL)
    return svc, qdrant


@celery_app.task(
    name="embedding.generate",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=120,
)
def generate_embedding(
    self,
    brand_id: str,
    text: str,
    source_hash: str,
    organization_id: str = "",
    source_type: str = "manual",
    brand_name: str = "",
) -> dict:
    """Generate and store a single brand mention embedding.

    Args:
        brand_id: UUID of the brand.
        text: Raw mention text to embed.
        source_hash: SHA-256 of the text (content_hash from BrandMentionEvent).
        organization_id: Tenant ID.
        source_type: e.g. "rss", "reddit", "manual".
        brand_name: Human-readable brand name for Qdrant payload.

    Returns:
        dict with status, brand_id, qdrant_point_id.
    """
    try:
        svc, qdrant = _get_services()

        items = [(brand_id, text)]
        hash_to_vec = svc.embed_batch(
            items=items,
            dag_run_id=f"celery:{self.request.id}",
            job_type="brand_mention",
        )

        if source_hash not in hash_to_vec:
            logger.warning(
                "Embedding not returned for hash",
                source_hash=source_hash,
                brand_id=brand_id,
            )
            return {"status": "error", "brand_id": brand_id, "hash": source_hash}

        from datetime import datetime, timezone

        point = {
            "content_hash": source_hash,
            "vector": hash_to_vec[source_hash],
            "brand_id": brand_id,
            "organization_id": organization_id,
            "source_type": source_type,
            "brand_name": brand_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        qdrant.upsert_brand_vectors([point])

        qdrant_id = f"{source_hash[:8]}..."
        logger.info(
            "Embedding stored",
            brand_id=brand_id,
            hash=source_hash,
            qdrant_id=qdrant_id,
        )
        return {"status": "ok", "brand_id": brand_id, "hash": source_hash}

    except Exception as exc:
        logger.exception("Embedding task failed", brand_id=brand_id, hash=source_hash)
        raise self.retry(exc=exc)


@celery_app.task(
    name="embedding.score_brand",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    time_limit=60,
)
def score_brand_sps(self, brand_id: str, dag_run_id: str = "celery") -> dict:
    """Compute and persist SPS scores for a brand against all intent clusters.

    Reads the brand's most recent vectors from Qdrant, aggregates them, and
    writes one SPS score row per intent cluster to the sps_scores table.
    """
    try:
        _, qdrant = _get_services()

        from qdrant_client.http.models import Filter, FieldCondition, MatchValue

        results = qdrant._client.scroll(
            collection_name="brand_embeddings",
            scroll_filter=Filter(
                must=[FieldCondition(key="brand_id", match=MatchValue(value=brand_id))]
            ),
            with_vectors=True,
            limit=100,
        )
        points = results[0]
        if not points:
            logger.info("No vectors found for brand", brand_id=brand_id)
            return {"status": "no_vectors", "brand_id": brand_id}

        from ml.scoring.proximity import aggregate_vectors, score_brand_vs_clusters

        vectors = [list(p.vector) for p in points if p.vector]  # type: ignore[arg-type]
        aggregated = aggregate_vectors(vectors)

        cluster_vectors = qdrant.get_all_concept_vectors()
        if not cluster_vectors:
            return {"status": "no_clusters", "brand_id": brand_id}

        sps_scores = score_brand_vs_clusters(aggregated, cluster_vectors)

        import psycopg2

        conn = psycopg2.connect(_DB_URL_SYNC)
        rows_written = 0
        try:
            with conn.cursor() as cur:
                for slug, score in sps_scores.items():
                    cur.execute(
                        """
                        INSERT INTO sps_scores
                          (id, brand_id, intent_cluster_slug, score, dag_run_id)
                        VALUES
                          (gen_random_uuid(), %s::uuid, %s, %s, %s)
                        """,
                        (brand_id, slug, score, dag_run_id),
                    )
                    rows_written += 1
            conn.commit()
        finally:
            conn.close()

        logger.info(
            "SPS scores computed",
            brand_id=brand_id,
            scores=sps_scores,
            rows_written=rows_written,
        )
        return {"status": "ok", "brand_id": brand_id, "sps_scores": sps_scores}

    except Exception as exc:
        logger.exception("score_brand_sps failed", brand_id=brand_id)
        raise self.retry(exc=exc)
