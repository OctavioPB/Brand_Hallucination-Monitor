"""One-shot script: create Qdrant collections and seed intent cluster vectors.

Run once after 'make up' to initialize the vector DB:
    python scripts/init_qdrant_collections.py

Idempotent — safe to re-run; existing collections are not deleted.
If OPENAI_API_KEY is not set, clusters are created with zero vectors
(useful for smoke-testing the collection structure without API spend).
"""
import logging
import os
import sys

# Add project root to path so ml/ imports work without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()


def main() -> None:
    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    db_url = os.environ.get(
        "DATABASE_URL_SYNC",
        "postgresql://hallucin8:hallucin8@localhost:5432/hallucin8",
    )

    from ml.embeddings.qdrant_store import QdrantStore

    logger.info("Connecting to Qdrant", url=qdrant_url)
    qdrant = QdrantStore(url=qdrant_url)
    qdrant.ensure_collections()
    logger.info("Collections ready")

    if not openai_key:
        logger.warning(
            "OPENAI_API_KEY not set — skipping intent cluster embedding. "
            "Run 'make intent-clusters' after setting the key."
        )
        return

    logger.info("Seeding intent cluster vectors via OpenAI...")

    import redis as redis_lib

    from infra.airflow.dags.dag_intent_cluster_refresh import INTENT_CLUSTERS
    from ml.embeddings.service import EmbeddingService, _sha256

    redis_client = redis_lib.from_url(redis_url, decode_responses=True)
    svc = EmbeddingService(
        api_key=openai_key,
        redis_client=redis_client,
        db_url=db_url,
    )

    items = [(c["slug"], c["description"]) for c in INTENT_CLUSTERS]
    hash_to_vec = svc.embed_batch(items=items, dag_run_id="init_script", job_type="intent_cluster")

    clusters_with_vectors = []
    for cluster in INTENT_CLUSTERS:
        h = _sha256(cluster["description"])
        vec = hash_to_vec.get(h)
        if vec is None:
            logger.warning("No vector for cluster", slug=cluster["slug"])
            continue
        clusters_with_vectors.append({**cluster, "vector": vec})

    stored = qdrant.upsert_concept_vectors(clusters_with_vectors)
    logger.info("Intent cluster vectors upserted", count=stored)

    # Verify
    concept_count = qdrant.count("concept_embeddings")
    brand_count = qdrant.count("brand_embeddings")
    competitor_count = qdrant.count("competitor_embeddings")
    logger.info(
        "Qdrant collections verified",
        concept_embeddings=concept_count,
        brand_embeddings=brand_count,
        competitor_embeddings=competitor_count,
    )


if __name__ == "__main__":
    main()
