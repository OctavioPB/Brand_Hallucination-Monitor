"""DAG: competitor_benchmark — daily competitor embedding snapshots.

For each active brand, queries competitor mentions from brand_mentions
(source_type='rss' or similar, tagged with competitor metadata), embeds
them, stores in competitor_embeddings, and computes cross-brand SPS delta
to identify semantic drift.

Runs daily at 02:00 UTC to avoid overlapping with the hourly embedding_batch.
"""
import json
import logging
import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task

logger = logging.getLogger(__name__)

_DB_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://hallucin8:hallucin8@postgres:5432/hallucin8",
)
_REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
_QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
_OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

_BATCH_LIMIT = int(os.environ.get("COMPETITOR_BATCH_LIMIT", "500"))


@dag(
    dag_id="competitor_benchmark",
    description="Daily: generate competitor embedding snapshots and SPS delta scores",
    schedule="0 2 * * *",
    start_date=datetime(2026, 5, 14),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=10),
        "execution_timeout": timedelta(minutes=20),
    },
    tags=["embeddings", "competitors", "sprint3"],
)
def competitor_benchmark() -> None:

    @task
    def fetch_competitor_mentions(batch_limit: int = _BATCH_LIMIT) -> list[dict]:
        """Fetch recent competitor mentions that haven't been embedded yet."""
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(_DB_URL)
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # competitor_id is set in metadata JSONB by the enrichment consumer
                cur.execute(
                    """
                    SELECT
                        bm.id::text,
                        bm.brand_id::text,
                        bm.organization_id,
                        bm.raw_text,
                        bm.content_hash,
                        bm.source_type,
                        bm.metadata->>'competitor_id' AS competitor_id,
                        bm.created_at::text
                    FROM brand_mentions bm
                    WHERE bm.metadata ? 'competitor_id'
                      AND bm.embedding_queued = false
                    ORDER BY bm.created_at DESC
                    LIMIT %s
                    """,
                    (batch_limit,),
                )
                rows = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

        logger.info("fetch_competitor_mentions: found %d rows", len(rows))
        return rows

    @task
    def embed_competitor_mentions(
        mentions: list[dict],
        run_id: str = "{{ run_id }}",
    ) -> list[dict]:
        """Embed competitor mentions and store in competitor_embeddings collection."""
        if not mentions:
            return []

        import redis as redis_lib

        from ml.embeddings.qdrant_store import QdrantStore
        from ml.embeddings.service import EmbeddingService

        redis_client = redis_lib.from_url(_REDIS_URL, decode_responses=True)
        svc = EmbeddingService(
            api_key=_OPENAI_API_KEY,
            redis_client=redis_client,
            db_url=_DB_URL,
        )
        qdrant = QdrantStore(url=_QDRANT_URL)

        items = [(m["id"], m["raw_text"]) for m in mentions]
        hash_to_vec = svc.embed_batch(
            items=items,
            dag_run_id=run_id,
            job_type="competitor",
        )

        points = []
        hash_to_mention = {m["content_hash"]: m for m in mentions}
        for content_hash, vector in hash_to_vec.items():
            mention = hash_to_mention.get(content_hash, {})
            points.append(
                {
                    "content_hash": content_hash,
                    "vector": vector,
                    "competitor_id": mention.get("competitor_id", ""),
                    "brand_id": mention.get("brand_id", ""),
                    "source_type": mention.get("source_type", "unknown"),
                    "created_at": mention.get("created_at", ""),
                }
            )

        stored = qdrant.upsert_competitor_vectors(points)
        logger.info("embed_competitor_mentions: stored %d competitor vectors", stored)
        return points

    @task
    def compute_sps_delta(
        embedded_mentions: list[dict],
        run_id: str = "{{ run_id }}",
    ) -> list[dict]:
        """Compute how each competitor's SPS compares to the monitored brand."""
        if not embedded_mentions:
            return []

        from ml.embeddings.qdrant_store import QdrantStore
        from ml.scoring.proximity import score_brand_vs_clusters

        qdrant = QdrantStore(url=_QDRANT_URL)
        cluster_vectors = qdrant.get_all_concept_vectors()
        if not cluster_vectors:
            logger.warning("No concept vectors in Qdrant, skipping SPS delta")
            return []

        deltas = []
        for mention in embedded_mentions:
            sps_scores = score_brand_vs_clusters(mention["vector"], cluster_vectors)
            deltas.append(
                {
                    "competitor_id": mention.get("competitor_id", ""),
                    "brand_id": mention.get("brand_id", ""),
                    "content_hash": mention["content_hash"],
                    "sps_scores": sps_scores,
                }
            )

        return deltas

    @task
    def persist_competitor_sps(
        deltas: list[dict],
        run_id: str = "{{ run_id }}",
    ) -> int:
        """Write competitor SPS deltas to sps_scores with competitor_id tagged in dag_run_id."""
        if not deltas:
            return 0

        import psycopg2

        rows_written = 0
        conn = psycopg2.connect(_DB_URL)
        try:
            with conn.cursor() as cur:
                for item in deltas:
                    brand_id = item.get("brand_id", "")
                    competitor_id = item.get("competitor_id", "")
                    if not brand_id:
                        continue
                    tagged_run = f"{run_id}:competitor:{competitor_id}"
                    for slug, score in item["sps_scores"].items():
                        cur.execute(
                            """
                            INSERT INTO sps_scores
                              (id, brand_id, intent_cluster_slug, score, dag_run_id)
                            VALUES
                              (gen_random_uuid(), %s::uuid, %s, %s, %s)
                            """,
                            (brand_id, slug, score, tagged_run),
                        )
                        rows_written += 1
            conn.commit()
        finally:
            conn.close()

        logger.info("persist_competitor_sps: wrote %d rows", rows_written)
        return rows_written

    # DAG wiring
    mentions = fetch_competitor_mentions()
    embedded = embed_competitor_mentions(mentions)
    deltas = compute_sps_delta(embedded)
    persist_competitor_sps(deltas)


competitor_benchmark_dag = competitor_benchmark()
