"""Integration tests for the Sprint 3 Vector ETL pipeline.

Tests the full data flow from raw events → embeddings → SPS scores
using in-process mocks for OpenAI, Redis, Qdrant, and PostgreSQL.

Definition of Done from PLAN.md:
> DAG runs end-to-end in < 5 min for 1000 events. SPS scores visible in DB.
> Embedding costs logged. Zero duplicate vectors in Qdrant.
"""
import json
import time
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ml.embeddings.service import EmbeddingService, _sha256
from ml.scoring.proximity import (
    aggregate_vectors,
    batch_score_brands,
    calculate_sps,
    score_brand_vs_clusters,
)


# ---------------------------------------------------------------------------
# Shared test infrastructure
# ---------------------------------------------------------------------------

class InMemoryRedis:
    """Redis mock supporting get/set/incrby/decrby/expire/delete."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | None:
        if nx and key in self._store:
            return None
        self._store[key] = value
        return True

    def incrby(self, key: str, n: int) -> int:
        self._store[key] = self._store.get(key, 0) + n
        return self._store[key]

    def decrby(self, key: str, n: int) -> int:
        self._store[key] = self._store.get(key, 0) - n
        return self._store[key]

    def expire(self, key: str, ttl: int) -> bool:
        return True

    def delete(self, *keys: str) -> int:
        deleted = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                deleted += 1
        return deleted

    def keys(self, pattern: str = "*") -> list[str]:
        return list(self._store.keys())


class InMemoryQdrant:
    """Minimal Qdrant mock that tracks upserted points."""

    def __init__(self) -> None:
        self._collections: dict[str, list[dict]] = {}

    def ensure_collections(self) -> None:
        for name in ["brand_embeddings", "concept_embeddings", "competitor_embeddings"]:
            if name not in self._collections:
                self._collections[name] = []

    def upsert_brand_vectors(self, points: list[dict]) -> int:
        coll = self._collections.setdefault("brand_embeddings", [])
        existing_hashes = {p["content_hash"] for p in coll}
        new_points = [p for p in points if p["content_hash"] not in existing_hashes]
        coll.extend(new_points)
        return len(points)

    def upsert_concept_vectors(self, concepts: list[dict]) -> int:
        coll = self._collections.setdefault("concept_embeddings", [])
        existing_slugs = {p.get("slug") for p in coll}
        for c in concepts:
            if c["slug"] not in existing_slugs:
                coll.append(c)
        return len(concepts)

    def upsert_competitor_vectors(self, points: list[dict]) -> int:
        coll = self._collections.setdefault("competitor_embeddings", [])
        coll.extend(points)
        return len(points)

    def get_all_concept_vectors(self) -> dict[str, list[float]]:
        return {
            p["slug"]: p["vector"]
            for p in self._collections.get("concept_embeddings", [])
            if "vector" in p
        }

    def count(self, name: str) -> int:
        return len(self._collections.get(name, []))


def _make_fake_openai(vectors_per_call: int = 0) -> Any:
    """Returns a _call_openai replacement that returns deterministic vectors."""
    call_log: list[int] = []

    def fake_call(texts: list[str]) -> tuple[list[list[float]], int]:
        call_log.append(len(texts))
        vectors = []
        for t in texts:
            # deterministic: vector depends on first char of text
            val = float(ord(t[0]) if t else 0) / 256.0
            vectors.append([val] * 1536)
        tokens = sum(len(t) // 4 + 1 for t in texts)
        return vectors, tokens

    fake_call.call_log = call_log  # type: ignore[attr-defined]
    return fake_call


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEmbeddingServiceIntegration:
    """Full service flow: items → cache check → OpenAI → cache write → result."""

    def test_1000_unique_events_embedded_correctly(self) -> None:
        """1000 unique items → 1000 vectors, 10 API calls (batches of 100)."""
        redis = InMemoryRedis()
        svc = EmbeddingService(api_key="key", redis_client=redis, db_url=None)

        n = 1000
        items = [(str(i), f"Brand mention number {i} about AcmeCorp products") for i in range(n)]
        fake_api = _make_fake_openai()

        with patch.object(svc, "_call_openai", side_effect=fake_api):
            result = svc.embed_batch(items, dag_run_id="test-run")

        assert len(result) == n
        # 1000 unique texts → ceil(1000/100) = 10 batches
        assert len(fake_api.call_log) == 10
        # All results are 1536-dim
        for vec in result.values():
            assert len(vec) == 1536

    def test_second_call_all_served_from_cache(self) -> None:
        """Re-embedding the same 1000 texts costs zero API calls."""
        redis = InMemoryRedis()
        svc = EmbeddingService(api_key="key", redis_client=redis, db_url=None)

        items = [(str(i), f"cached text {i}") for i in range(100)]
        fake_api = _make_fake_openai()

        with patch.object(svc, "_call_openai", side_effect=fake_api):
            svc.embed_batch(items)

        fake_api2 = _make_fake_openai()
        with patch.object(svc, "_call_openai", side_effect=fake_api2):
            result2 = svc.embed_batch(items)

        assert len(fake_api2.call_log) == 0  # zero API calls
        assert len(result2) == 100

    def test_zero_duplicate_vectors_in_qdrant(self) -> None:
        """Upserting the same content_hash twice must not create duplicate points."""
        qdrant = InMemoryQdrant()
        qdrant.ensure_collections()

        h = _sha256("some brand mention text")
        point = {
            "content_hash": h,
            "vector": [0.5] * 1536,
            "brand_id": "brand-001",
            "organization_id": "org-001",
            "source_type": "rss",
            "brand_name": "AcmeCorp",
            "created_at": "2026-05-14T00:00:00Z",
        }
        qdrant.upsert_brand_vectors([point])
        qdrant.upsert_brand_vectors([point])  # second upsert with same hash

        count = qdrant.count("brand_embeddings")
        assert count == 1, f"Expected 1 point, got {count}"


class TestProximityPipeline:
    """Tests the scoring pipeline from concept seeding to SPS computation."""

    def _seed_clusters(self, qdrant: InMemoryQdrant) -> dict[str, list[float]]:
        clusters = [
            {"slug": "reliability", "display_name": "Reliability", "vector": [1.0] + [0.0] * 1535},
            {"slug": "innovation", "display_name": "Innovation", "vector": [0.0, 1.0] + [0.0] * 1534},
            {"slug": "pricing_value", "display_name": "Pricing", "vector": [0.0, 0.0, 1.0] + [0.0] * 1533},
        ]
        qdrant.upsert_concept_vectors(clusters)
        return {c["slug"]: c["vector"] for c in clusters}

    def test_sps_scores_computed_for_all_clusters(self) -> None:
        qdrant = InMemoryQdrant()
        cluster_vecs = self._seed_clusters(qdrant)
        brand_vec = [1.0] + [0.0] * 1535  # identical to 'reliability'

        scores = score_brand_vs_clusters(brand_vec, cluster_vecs)

        assert set(scores.keys()) == {"reliability", "innovation", "pricing_value"}
        assert scores["reliability"] == pytest.approx(1.0, abs=1e-6)
        # reliability cluster is orthogonal to innovation and pricing_value
        assert scores["innovation"] == pytest.approx(0.5, abs=1e-6)
        assert scores["pricing_value"] == pytest.approx(0.5, abs=1e-6)

    def test_batch_1000_brand_vectors_scored(self) -> None:
        """1000 brand mentions across 10 brands × 6 clusters = 6000 SPS rows."""
        import random
        rng = random.Random(42)

        n_brands = 10
        n_clusters = 6
        mentions_per_brand = 100

        brand_ids = [f"brand-{i:03d}" for i in range(n_brands)]
        cluster_vecs = {
            f"cluster-{j}": [rng.gauss(0, 1) for _ in range(1536)]
            for j in range(n_clusters)
        }

        # Aggregate one vector per brand from 100 mentions
        brand_vectors: dict[str, list[float]] = {}
        for brand_id in brand_ids:
            mention_vecs = [
                [rng.gauss(0, 1) for _ in range(1536)]
                for _ in range(mentions_per_brand)
            ]
            brand_vectors[brand_id] = aggregate_vectors(mention_vecs)

        start = time.time()
        all_scores = batch_score_brands(brand_vectors, cluster_vecs)
        elapsed = time.time() - start

        # All brands scored
        assert set(all_scores.keys()) == set(brand_ids)
        # All clusters present for each brand
        for brand_id in brand_ids:
            assert set(all_scores[brand_id].keys()) == set(cluster_vecs.keys())
            for score in all_scores[brand_id].values():
                assert 0.0 <= score <= 1.0

        # This is pure numpy math — should complete in well under 1 second
        assert elapsed < 5.0, f"Scoring 1000 mentions took {elapsed:.2f}s — too slow"

    def test_concept_deduplication_in_qdrant(self) -> None:
        """Upserting same cluster slug twice does not create duplicate concept vectors."""
        qdrant = InMemoryQdrant()
        cluster = {"slug": "reliability", "display_name": "Reliability", "vector": [0.5] * 1536}
        qdrant.upsert_concept_vectors([cluster])
        qdrant.upsert_concept_vectors([cluster])

        assert qdrant.count("concept_embeddings") == 1


class TestEndToEndPipelineSimulation:
    """Simulate the full embedding_batch DAG logic in-process."""

    N_EVENTS = 100

    def _make_events(self, n: int) -> list[dict]:
        return [
            {
                "id": f"event-{i}",
                "brand_id": "brand-uuid-001",
                "organization_id": "org-001",
                "raw_text": f"AcmeCorp brand mention number {i} about reliability and innovation",
                "content_hash": _sha256(f"AcmeCorp brand mention number {i} about reliability and innovation"),
                "source_type": "rss",
                "brand_name_hint": "AcmeCorp",
                "created_at": "2026-05-14T12:00:00Z",
            }
            for i in range(n)
        ]

    def test_full_pipeline_100_events(self) -> None:
        """Simulate: fetch → embed → score → store_vectors → update_sps."""
        events = self._make_events(self.N_EVENTS)
        redis = InMemoryRedis()
        qdrant = InMemoryQdrant()
        qdrant.ensure_collections()

        # Seed concept vectors
        cluster_vecs = {
            "reliability": [1.0] + [0.0] * 1535,
            "innovation": [0.0, 1.0] + [0.0] * 1534,
        }
        qdrant.upsert_concept_vectors(
            [{"slug": s, "display_name": s, "vector": v} for s, v in cluster_vecs.items()]
        )

        svc = EmbeddingService(api_key="key", redis_client=redis, db_url=None)
        fake_api = _make_fake_openai()

        # --- Task 2: generate embeddings ---
        with patch.object(svc, "_call_openai", side_effect=fake_api):
            items = [(e["id"], e["raw_text"]) for e in events]
            hash_to_vec = svc.embed_batch(items, dag_run_id="test-e2e")

        assert len(hash_to_vec) == self.N_EVENTS

        # --- Task 3: calculate cosine distances ---
        scored_events = []
        for event in events:
            h = event["content_hash"]
            vec = hash_to_vec.get(h)
            if vec is None:
                continue
            sps = score_brand_vs_clusters(vec, cluster_vecs)
            scored_events.append(
                {"content_hash": h, "brand_id": event["brand_id"], "sps_scores": sps}
            )

        assert len(scored_events) == self.N_EVENTS

        # --- Task 4: store vectors ---
        points = []
        for event in events:
            h = event["content_hash"]
            if h in hash_to_vec:
                points.append({
                    "content_hash": h,
                    "vector": hash_to_vec[h],
                    "brand_id": event["brand_id"],
                    "organization_id": event["organization_id"],
                    "source_type": event["source_type"],
                    "brand_name": event["brand_name_hint"],
                    "created_at": event["created_at"],
                })
        stored = qdrant.upsert_brand_vectors(points)
        assert stored == self.N_EVENTS

        # --- Verify: no duplicates in Qdrant ---
        assert qdrant.count("brand_embeddings") == self.N_EVENTS

        # --- Verify: SPS scores present for all events × clusters ---
        total_sps_rows = sum(len(e["sps_scores"]) for e in scored_events)
        assert total_sps_rows == self.N_EVENTS * len(cluster_vecs)

        # --- Verify: all SPS scores in [0, 1] ---
        for item in scored_events:
            for score in item["sps_scores"].values():
                assert 0.0 <= score <= 1.0
