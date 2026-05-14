"""DAG: intent_cluster_refresh — weekly refresh of intent cluster centroid vectors.

Embeds the canonical description of each intent cluster and upserts to
concept_embeddings in Qdrant. Running weekly ensures centroids reflect
any model updates while keeping API costs low (~$0.001 per run).

Intent clusters are defined here rather than in DB because they change
rarely and require product-level approval before modification.
"""
import logging
import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task

logger = logging.getLogger(__name__)

_REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
_QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
_OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
_DB_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://hallucin8:hallucin8@postgres:5432/hallucin8",
)

# Canonical intent clusters — modify only with product approval.
# description is the text that gets embedded as the centroid.
INTENT_CLUSTERS: list[dict] = [
    {
        "slug": "reliability",
        "display_name": "Reliability & Trust",
        "description": (
            "The brand is dependable, consistent, and trustworthy. Products and services "
            "work as expected, have low failure rates, and customers can count on them."
        ),
    },
    {
        "slug": "innovation",
        "display_name": "Innovation & Technology",
        "description": (
            "The brand leads in technological advancement, introduces new products, "
            "invests in R&D, and is perceived as forward-thinking and cutting-edge."
        ),
    },
    {
        "slug": "pricing_value",
        "display_name": "Pricing & Value",
        "description": (
            "The brand offers competitive pricing, good value for money, transparent costs, "
            "and affordable options that appeal to cost-conscious buyers."
        ),
    },
    {
        "slug": "market_leadership",
        "display_name": "Market Leadership",
        "description": (
            "The brand is recognized as a leader in its industry, has significant market share, "
            "strong brand recognition, and is recommended as the go-to choice by experts."
        ),
    },
    {
        "slug": "compliance",
        "display_name": "Compliance & Security",
        "description": (
            "The brand meets regulatory requirements, prioritizes data privacy and security, "
            "holds relevant certifications, and is trusted for handling sensitive information."
        ),
    },
    {
        "slug": "support_quality",
        "display_name": "Support & Customer Experience",
        "description": (
            "The brand provides excellent customer support, responsive service, clear documentation, "
            "and a smooth onboarding experience that reduces friction for customers."
        ),
    },
]


@dag(
    dag_id="intent_cluster_refresh",
    description="Weekly: refresh intent cluster centroid vectors in Qdrant",
    schedule="0 3 * * 0",  # Sundays at 03:00 UTC
    start_date=datetime(2026, 5, 14),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=5),
    },
    tags=["embeddings", "intent-clusters", "sprint3"],
)
def intent_cluster_refresh() -> None:

    @task
    def embed_cluster_descriptions(run_id: str = "{{ run_id }}") -> list[dict]:
        """Embed each intent cluster description and return with vectors."""
        import redis as redis_lib

        from ml.embeddings.service import EmbeddingService

        redis_client = redis_lib.from_url(_REDIS_URL, decode_responses=True)
        svc = EmbeddingService(
            api_key=_OPENAI_API_KEY,
            redis_client=redis_client,
            db_url=_DB_URL,
        )

        items = [(c["slug"], c["description"]) for c in INTENT_CLUSTERS]
        from ml.embeddings.service import _sha256

        hash_to_vec = svc.embed_batch(
            items=items,
            dag_run_id=run_id,
            job_type="intent_cluster",
        )

        enriched = []
        for cluster in INTENT_CLUSTERS:
            h = _sha256(cluster["description"])
            vec = hash_to_vec.get(h)
            if vec is None:
                logger.warning("No vector generated for cluster %s", cluster["slug"])
                continue
            enriched.append(
                {
                    "slug": cluster["slug"],
                    "display_name": cluster["display_name"],
                    "description": cluster["description"],
                    "vector": vec,
                }
            )

        logger.info("embed_cluster_descriptions: embedded %d clusters", len(enriched))
        return enriched

    @task
    def upsert_to_qdrant(clusters: list[dict]) -> dict:
        """Upsert concept vectors to Qdrant and ensure collections exist."""
        if not clusters:
            return {"upserted": 0}

        from ml.embeddings.qdrant_store import QdrantStore

        qdrant = QdrantStore(url=_QDRANT_URL)
        qdrant.ensure_collections()
        stored = qdrant.upsert_concept_vectors(clusters)

        logger.info("upsert_to_qdrant: stored %d concept vectors", stored)
        return {"upserted": stored}

    @task
    def sync_clusters_to_db(clusters: list[dict]) -> int:
        """Upsert intent cluster slugs and display names to intent_clusters table."""
        if not clusters:
            return 0

        import psycopg2

        conn = psycopg2.connect(_DB_URL)
        upserted = 0
        try:
            with conn.cursor() as cur:
                for cluster in clusters:
                    cur.execute(
                        """
                        INSERT INTO intent_clusters (id, slug, display_name)
                        VALUES (gen_random_uuid(), %s, %s)
                        ON CONFLICT (slug) DO UPDATE
                          SET display_name = EXCLUDED.display_name
                        """,
                        (cluster["slug"], cluster["display_name"]),
                    )
                    upserted += 1
            conn.commit()
        finally:
            conn.close()

        logger.info("sync_clusters_to_db: upserted %d clusters", upserted)
        return upserted

    # DAG wiring — upsert to Qdrant and DB in parallel after embedding
    clusters = embed_cluster_descriptions()
    upsert_to_qdrant(clusters)
    sync_clusters_to_db(clusters)


intent_cluster_refresh_dag = intent_cluster_refresh()
