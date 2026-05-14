"""DAG: embedding_batch — hourly Vector ETL for brand mention embeddings.

Pipeline:
  fetch_pending_events
    → generate_embeddings  (OpenAI text-embedding-3-small, batches of 100)
    → calculate_cosine_distances  (vs. intent cluster centroids in Qdrant)
    → [store_vectors, update_sps_scores]  (parallel)
    → mark_processed

Intermediate vector storage: Redis keys "dag:{run_id}:emb:{content_hash}" with
1h TTL — avoids XCom size limits while keeping tasks decoupled.

Scheduling note: max_active_runs=1 prevents concurrent runs from double-processing
the same pending mentions.
"""
import json
import logging
import os
import time
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

_BATCH_LIMIT = int(os.environ.get("EMBEDDING_BATCH_LIMIT", "1000"))
_REDIS_VEC_TTL = 3600  # 1h — vectors in transit between tasks
_REDIS_VEC_PREFIX = "dag:emb:vec:"


@dag(
    dag_id="embedding_batch",
    description="Hourly: embed pending brand mentions, score vs intent clusters, store in Qdrant",
    schedule="@hourly",
    start_date=datetime(2026, 5, 14),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "execution_timeout": timedelta(minutes=10),
    },
    tags=["embeddings", "sprint3"],
)
def embedding_batch() -> None:

    @task
    def fetch_pending_events(batch_limit: int = _BATCH_LIMIT) -> list[dict]:
        """Read brand_mentions where embedding_queued=false, up to batch_limit rows."""
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(_DB_URL)
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id::text, brand_id::text, organization_id,
                        raw_text, content_hash, source_type,
                        source_url, brand_name_hint,
                        created_at::text
                    FROM brand_mentions
                    WHERE embedding_queued = false
                    ORDER BY created_at ASC
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                    """,
                    (batch_limit,),
                )
                rows = [dict(r) for r in cur.fetchall()]
            conn.commit()
        finally:
            conn.close()

        logger.info("fetch_pending_events: found %d rows", len(rows))
        return rows

    @task
    def generate_embeddings(events: list[dict], run_id: str = "{{ run_id }}") -> list[str]:
        """Embed raw_text for each event; store vectors in Redis. Returns content_hashes."""
        if not events:
            return []

        import redis as redis_lib

        from ml.embeddings.service import EmbeddingService

        redis_client = redis_lib.from_url(_REDIS_URL, decode_responses=True)
        svc = EmbeddingService(
            api_key=_OPENAI_API_KEY,
            redis_client=redis_client,
            db_url=_DB_URL,
        )

        items = [(e["id"], e["raw_text"]) for e in events]
        hash_to_vec = svc.embed_batch(
            items=items,
            dag_run_id=run_id,
            job_type="brand_mention",
        )

        # Store in Redis with 1h TTL for downstream tasks
        for content_hash, vector in hash_to_vec.items():
            redis_client.set(
                f"{_REDIS_VEC_PREFIX}{run_id}:{content_hash}",
                json.dumps(vector),
                ex=_REDIS_VEC_TTL,
            )

        logger.info("generate_embeddings: embedded %d texts", len(hash_to_vec))
        return list(hash_to_vec.keys())

    @task
    def calculate_cosine_distances(
        content_hashes: list[str],
        events: list[dict],
        run_id: str = "{{ run_id }}",
    ) -> list[dict]:
        """Score each embedded event against intent cluster centroids.

        Returns list of dicts: {content_hash, brand_id, sps_scores: {slug: float}}
        """
        if not content_hashes:
            return []

        import redis as redis_lib

        from ml.embeddings.qdrant_store import QdrantStore
        from ml.scoring.proximity import score_brand_vs_clusters

        redis_client = redis_lib.from_url(_REDIS_URL, decode_responses=True)
        qdrant = QdrantStore(url=_QDRANT_URL)

        cluster_vectors = qdrant.get_all_concept_vectors()
        if not cluster_vectors:
            logger.warning("No concept vectors found in Qdrant — skipping SPS calculation")
            return []

        hash_to_event = {e["content_hash"]: e for e in events}
        scored: list[dict] = []

        for content_hash in content_hashes:
            raw = redis_client.get(f"{_REDIS_VEC_PREFIX}{run_id}:{content_hash}")
            if raw is None:
                logger.warning("Vector not found in Redis", content_hash=content_hash)
                continue

            vector = json.loads(raw)
            sps_scores = score_brand_vs_clusters(vector, cluster_vectors)
            event = hash_to_event.get(content_hash, {})

            scored.append(
                {
                    "content_hash": content_hash,
                    "brand_id": event.get("brand_id", ""),
                    "sps_scores": sps_scores,
                }
            )

        logger.info("calculate_cosine_distances: scored %d events", len(scored))
        return scored

    @task
    def store_vectors(
        content_hashes: list[str],
        events: list[dict],
        run_id: str = "{{ run_id }}",
    ) -> list[str]:
        """Upsert brand embedding vectors to Qdrant brand_embeddings collection."""
        if not content_hashes:
            return []

        import redis as redis_lib

        from ml.embeddings.qdrant_store import QdrantStore

        redis_client = redis_lib.from_url(_REDIS_URL, decode_responses=True)
        qdrant = QdrantStore(url=_QDRANT_URL)

        hash_to_event = {e["content_hash"]: e for e in events}
        points = []

        for content_hash in content_hashes:
            raw = redis_client.get(f"{_REDIS_VEC_PREFIX}{run_id}:{content_hash}")
            if raw is None:
                continue
            event = hash_to_event.get(content_hash, {})
            points.append(
                {
                    "content_hash": content_hash,
                    "vector": json.loads(raw),
                    "brand_id": event.get("brand_id", ""),
                    "organization_id": event.get("organization_id", ""),
                    "source_type": event.get("source_type", "unknown"),
                    "brand_name": event.get("brand_name_hint", ""),
                    "created_at": event.get("created_at", ""),
                }
            )

        stored = qdrant.upsert_brand_vectors(points)
        logger.info("store_vectors: upserted %d points to Qdrant", stored)
        return [p["content_hash"] for p in points]

    @task
    def update_sps_scores(scored_events: list[dict], run_id: str = "{{ run_id }}") -> int:
        """Write SPS scores to PostgreSQL sps_scores table."""
        if not scored_events:
            return 0

        import psycopg2

        rows_written = 0
        conn = psycopg2.connect(_DB_URL)
        try:
            with conn.cursor() as cur:
                for item in scored_events:
                    brand_id = item["brand_id"]
                    if not brand_id:
                        continue
                    for slug, score in item["sps_scores"].items():
                        cur.execute(
                            """
                            INSERT INTO sps_scores
                              (id, brand_id, intent_cluster_slug, score, dag_run_id)
                            VALUES
                              (gen_random_uuid(), %s::uuid, %s, %s, %s)
                            """,
                            (brand_id, slug, score, run_id),
                        )
                        rows_written += 1
            conn.commit()
        finally:
            conn.close()

        logger.info("update_sps_scores: wrote %d rows", rows_written)
        return rows_written

    @task
    def mark_processed(
        stored_hashes: list[str],
        sps_rows_written: int,
        events: list[dict],
        run_id: str = "{{ run_id }}",
    ) -> dict:
        """Mark brand_mentions as embedding_queued=true; clean Redis temp keys."""
        if not stored_hashes:
            return {"processed": 0, "sps_rows": 0}

        import psycopg2
        import redis as redis_lib

        conn = psycopg2.connect(_DB_URL)
        processed_count = 0
        try:
            with conn.cursor() as cur:
                # Bulk update using IN clause with content_hashes
                placeholders = ",".join(["%s"] * len(stored_hashes))
                cur.execute(
                    f"""
                    UPDATE brand_mentions
                    SET embedding_queued = true
                    WHERE content_hash IN ({placeholders})
                    """,
                    stored_hashes,
                )
                processed_count = cur.rowcount
            conn.commit()
        finally:
            conn.close()

        # Clean Redis temp vectors
        redis_client = redis_lib.from_url(_REDIS_URL, decode_responses=True)
        keys_deleted = 0
        for h in stored_hashes:
            deleted = redis_client.delete(f"{_REDIS_VEC_PREFIX}{run_id}:{h}")
            keys_deleted += deleted

        summary = {
            "processed": processed_count,
            "sps_rows": sps_rows_written,
            "redis_keys_cleaned": keys_deleted,
            "run_id": run_id,
        }
        logger.info("mark_processed: %s", summary)
        return summary

    # ------------------------------------------------------------------
    # DAG wiring
    # ------------------------------------------------------------------
    events = fetch_pending_events()
    hashes = generate_embeddings(events)
    scored = calculate_cosine_distances(hashes, events)
    stored = store_vectors(hashes, events)
    sps_count = update_sps_scores(scored)
    mark_processed(stored, sps_count, events)


embedding_batch_dag = embedding_batch()
