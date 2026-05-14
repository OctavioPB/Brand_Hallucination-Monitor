"""EmbeddingService — sync batch embedding with Redis cache, token bucket, and cost tracking.

Design decisions:
- Sync (not async) because the primary caller is Airflow tasks; FastAPI callers use
  run_in_executor.
- Token bucket via Redis so that concurrent Celery workers + Airflow don't jointly
  exceed the 1M token/min OpenAI rate limit.
- Cache key: "emb:v1:{sha256(text)}" — model-version-prefixed to allow future migration.
- Cost tracked in PostgreSQL embedding_costs; use dag_run_id="celery" for ad-hoc calls.
"""
import hashlib
import json
import logging
import math
import time
from decimal import Decimal
from typing import Any

import psycopg2

logger = logging.getLogger(__name__)

# text-embedding-3-small pricing (May 2026): $0.02 / 1M tokens
_COST_PER_MILLION_TOKENS = Decimal("0.02")

_CACHE_PREFIX = "emb:v1:"
_CACHE_TTL_SECONDS = 86_400  # 24h

# Token bucket: 1M tokens/min window
_TOKEN_BUCKET_KEY = "tb:openai:embeddings"
_TOKEN_BUCKET_LIMIT = 1_000_000
_TOKEN_BUCKET_WINDOW_SECONDS = 60
_TOKEN_BUCKET_POLL_INTERVAL = 0.5


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class EmbeddingService:
    """Batch embedding with Redis caching, rate limiting, and cost logging."""

    MODEL = "text-embedding-3-small"
    DIMENSIONS = 1536
    BATCH_SIZE = 100  # OpenAI max per request

    def __init__(
        self,
        api_key: str,
        redis_client: Any,  # redis.Redis — Any to avoid hard import in tests
        db_url: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._redis = redis_client
        self._db_url = db_url

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def embed_batch(
        self,
        items: list[tuple[str, str]],
        dag_run_id: str = "celery",
        job_type: str = "brand_mention",
    ) -> dict[str, list[float]]:
        """Embed a list of (id, text) pairs.

        Args:
            items: List of (identifier, text) tuples. Identifier is only used for
                   correlating results — the cache key is always SHA-256(text).
            dag_run_id: Airflow dag_run_id or "celery" for Celery-initiated calls.
            job_type: "brand_mention" | "competitor" | "intent_cluster"

        Returns:
            dict mapping SHA-256(text) → 1536-dim float vector.
        """
        if not items:
            return {}

        hashes = [_sha256(text) for _, text in items]
        hash_to_text = {_sha256(text): text for _, text in items}

        # 1. Check Redis cache
        cached = self._check_cache(list(set(hashes)))
        uncached_hashes = [h for h in hash_to_text if h not in cached]

        result: dict[str, list[float]] = {**cached}

        if not uncached_hashes:
            logger.info(
                "All embeddings served from cache",
                cached=len(cached),
                dag_run_id=dag_run_id,
            )
            if self._db_url:
                self._log_cost(
                    dag_run_id=dag_run_id,
                    job_type=job_type,
                    tokens_input=0,
                    n_vectors=0,
                    n_cached=len(cached),
                )
            return result

        # 2. Call OpenAI in batches of BATCH_SIZE
        texts_to_embed = [hash_to_text[h] for h in uncached_hashes]
        total_tokens = 0

        for batch_start in range(0, len(texts_to_embed), self.BATCH_SIZE):
            batch = texts_to_embed[batch_start : batch_start + self.BATCH_SIZE]
            batch_hashes = uncached_hashes[batch_start : batch_start + self.BATCH_SIZE]

            # Estimate tokens to enforce rate limit (4 chars ≈ 1 token)
            estimated_tokens = sum(math.ceil(len(t) / 4) for t in batch)
            self._consume_tokens(estimated_tokens)

            vectors, tokens_used = self._call_openai(batch)
            total_tokens += tokens_used

            # 3. Cache results and accumulate
            for h, vec in zip(batch_hashes, vectors):
                self._set_cache(h, vec)
                result[h] = vec

        # 4. Log cost
        cost = (Decimal(total_tokens) / Decimal(1_000_000)) * _COST_PER_MILLION_TOKENS
        if self._db_url:
            self._log_cost(
                dag_run_id=dag_run_id,
                job_type=job_type,
                tokens_input=total_tokens,
                n_vectors=len(uncached_hashes),
                n_cached=len(cached),
                cost_usd=cost,
            )

        logger.info(
            "Embedding batch complete",
            total=len(items),
            cached=len(cached),
            new_embeddings=len(uncached_hashes),
            tokens_used=total_tokens,
            cost_usd=float(cost),
            dag_run_id=dag_run_id,
        )
        return result

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _check_cache(self, hashes: list[str]) -> dict[str, list[float]]:
        cached: dict[str, list[float]] = {}
        for h in hashes:
            raw = self._redis.get(f"{_CACHE_PREFIX}{h}")
            if raw is not None:
                cached[h] = json.loads(raw)
        return cached

    def _set_cache(self, content_hash: str, vector: list[float]) -> None:
        try:
            self._redis.set(
                f"{_CACHE_PREFIX}{content_hash}",
                json.dumps(vector),
                ex=_CACHE_TTL_SECONDS,
            )
        except Exception:
            logger.warning("Failed to cache embedding", hash=content_hash)

    # ------------------------------------------------------------------
    # Token bucket (Redis sliding window per 60s)
    # ------------------------------------------------------------------

    def _consume_tokens(self, n_tokens: int) -> None:
        """Block until the rate limit allows n_tokens to be consumed."""
        while True:
            bucket_key = f"{_TOKEN_BUCKET_KEY}:{int(time.time()) // _TOKEN_BUCKET_WINDOW_SECONDS}"
            try:
                current = self._redis.incrby(bucket_key, n_tokens)
                if current == n_tokens:
                    # First write in this window — set expiry
                    self._redis.expire(bucket_key, _TOKEN_BUCKET_WINDOW_SECONDS * 2)
                if current <= _TOKEN_BUCKET_LIMIT:
                    return
                # Over limit — roll back and wait
                self._redis.decrby(bucket_key, n_tokens)
                time.sleep(_TOKEN_BUCKET_POLL_INTERVAL)
            except Exception:
                # Redis unavailable — proceed without rate limiting (fail-open)
                logger.warning("Token bucket Redis unavailable, proceeding without rate limit")
                return

    # ------------------------------------------------------------------
    # OpenAI call
    # ------------------------------------------------------------------

    def _call_openai(self, texts: list[str]) -> tuple[list[list[float]], int]:
        """Call OpenAI embeddings API. Returns (vectors, tokens_used)."""
        try:
            from openai import OpenAI  # lazy import — not required unless actually called
        except ImportError as exc:
            raise RuntimeError(
                "openai package not installed. Add 'openai>=1.30.0' to dependencies."
            ) from exc

        client = OpenAI(api_key=self._api_key)
        response = client.embeddings.create(
            model=self.MODEL,
            input=texts,
            dimensions=self.DIMENSIONS,
        )
        vectors = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        tokens_used: int = response.usage.total_tokens
        return vectors, tokens_used

    # ------------------------------------------------------------------
    # Cost logging
    # ------------------------------------------------------------------

    def _log_cost(
        self,
        dag_run_id: str,
        job_type: str,
        tokens_input: int,
        n_vectors: int,
        n_cached: int,
        cost_usd: Decimal = Decimal("0"),
    ) -> None:
        if not self._db_url:
            return
        try:
            conn = psycopg2.connect(self._db_url)
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO embedding_costs
                          (id, dag_run_id, model, job_type, tokens_input, n_vectors,
                           n_cached, cost_usd)
                        VALUES
                          (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            dag_run_id,
                            self.MODEL,
                            job_type,
                            tokens_input,
                            n_vectors,
                            n_cached,
                            str(cost_usd),
                        ),
                    )
            conn.close()
        except Exception:
            logger.exception("Failed to log embedding cost", dag_run_id=dag_run_id)
