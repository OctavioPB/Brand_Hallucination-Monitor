"""QdrantStore — collection management and vector upsert/search helpers.

Collections:
  brand_embeddings    — 1536-dim cosine; one point per brand mention
  concept_embeddings  — 1536-dim cosine; intent cluster centroids
  competitor_embeddings — 1536-dim cosine; competitor mention snapshots

Payload schema (brand_embeddings):
  brand_id: str
  organization_id: str
  source_type: str
  content_hash: str  ← used as deterministic point ID to prevent duplicates
  created_at: str (ISO 8601)
  brand_name: str
"""
import hashlib
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

BRAND_EMBEDDINGS = "brand_embeddings"
CONCEPT_EMBEDDINGS = "concept_embeddings"
COMPETITOR_EMBEDDINGS = "competitor_embeddings"

_VECTOR_SIZE = 1536
_DISTANCE = "Cosine"

_COLLECTIONS = [BRAND_EMBEDDINGS, CONCEPT_EMBEDDINGS, COMPETITOR_EMBEDDINGS]


def _hash_to_uuid(content_hash: str) -> str:
    """Convert a SHA-256 hex string to a UUID v5 (deterministic, collision-free)."""
    return str(uuid.UUID(bytes=bytes.fromhex(content_hash[:32])))


class QdrantStore:
    """Thin wrapper around qdrant-client for hallucin8's collections."""

    def __init__(self, url: str, api_key: str | None = None) -> None:
        try:
            from qdrant_client import QdrantClient  # lazy import
            from qdrant_client.http.models import Distance, VectorParams
        except ImportError as exc:
            raise RuntimeError(
                "qdrant-client not installed. Add 'qdrant-client>=1.9.0' to dependencies."
            ) from exc

        self._client = QdrantClient(url=url, api_key=api_key)
        self._Distance = Distance
        self._VectorParams = VectorParams

    # ------------------------------------------------------------------
    # Collection lifecycle
    # ------------------------------------------------------------------

    def ensure_collections(self) -> None:
        """Create all required collections if they don't already exist."""
        existing = {c.name for c in self._client.get_collections().collections}
        for name in _COLLECTIONS:
            if name not in existing:
                self._client.create_collection(
                    collection_name=name,
                    vectors_config=self._VectorParams(
                        size=_VECTOR_SIZE,
                        distance=self._Distance.Cosine,
                    ),
                )
                logger.info("Created Qdrant collection", collection=name)
            else:
                logger.debug("Qdrant collection already exists", collection=name)

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------

    def upsert_brand_vectors(self, points: list[dict[str, Any]]) -> int:
        """Upsert brand mention vectors to brand_embeddings.

        Args:
            points: list of dicts with keys:
                content_hash (str), vector (list[float]), brand_id (str),
                organization_id (str), source_type (str), brand_name (str),
                created_at (str)

        Returns:
            Number of points upserted.
        """
        from qdrant_client.http.models import PointStruct

        qdrant_points = [
            PointStruct(
                id=_hash_to_uuid(p["content_hash"]),
                vector=p["vector"],
                payload={
                    "brand_id": p["brand_id"],
                    "organization_id": p.get("organization_id", ""),
                    "source_type": p.get("source_type", "unknown"),
                    "content_hash": p["content_hash"],
                    "brand_name": p.get("brand_name", ""),
                    "created_at": p.get("created_at", ""),
                },
            )
            for p in points
        ]

        self._client.upsert(collection_name=BRAND_EMBEDDINGS, points=qdrant_points)
        return len(qdrant_points)

    def upsert_concept_vectors(self, concepts: list[dict[str, Any]]) -> int:
        """Upsert intent cluster centroid vectors to concept_embeddings.

        Args:
            concepts: list of dicts with keys:
                slug (str), display_name (str), vector (list[float]),
                description (str)
        """
        from qdrant_client.http.models import PointStruct

        qdrant_points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"concept:{c['slug']}")),
                vector=c["vector"],
                payload={
                    "slug": c["slug"],
                    "display_name": c.get("display_name", c["slug"]),
                    "description": c.get("description", ""),
                },
            )
            for c in concepts
        ]

        self._client.upsert(collection_name=CONCEPT_EMBEDDINGS, points=qdrant_points)
        return len(qdrant_points)

    def upsert_competitor_vectors(self, points: list[dict[str, Any]]) -> int:
        """Upsert competitor mention vectors to competitor_embeddings."""
        from qdrant_client.http.models import PointStruct

        qdrant_points = [
            PointStruct(
                id=_hash_to_uuid(p["content_hash"]),
                vector=p["vector"],
                payload={
                    "competitor_id": p.get("competitor_id", ""),
                    "brand_id": p.get("brand_id", ""),
                    "content_hash": p["content_hash"],
                    "source_type": p.get("source_type", "unknown"),
                    "created_at": p.get("created_at", ""),
                },
            )
            for p in points
        ]

        self._client.upsert(collection_name=COMPETITOR_EMBEDDINGS, points=qdrant_points)
        return len(qdrant_points)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_all_concept_vectors(self) -> dict[str, list[float]]:
        """Fetch all intent cluster centroid vectors. Returns slug → vector dict."""
        results = self._client.scroll(
            collection_name=CONCEPT_EMBEDDINGS,
            with_vectors=True,
            with_payload=True,
            limit=100,
        )
        slug_to_vector: dict[str, list[float]] = {}
        for point in results[0]:
            if point.vector and point.payload:
                slug = point.payload.get("slug", "")
                if slug:
                    slug_to_vector[slug] = list(point.vector)  # type: ignore[arg-type]
        return slug_to_vector

    def count(self, collection_name: str) -> int:
        return self._client.count(collection_name=collection_name).count
