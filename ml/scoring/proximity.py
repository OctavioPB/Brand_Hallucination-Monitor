"""Semantic Proximity Scoring — cosine similarity between brand and concept vectors.

SPS (Semantic Proximity Score): float [0, 1] where 1 = identical direction in
embedding space. Computed as cosine similarity between a brand's aggregated embedding
and an intent cluster centroid.

This module is pure numpy — no network calls, no DB access. Side-effect-free.
"""
import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


def calculate_sps(brand_vector: list[float], concept_vector: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors.

    Args:
        brand_vector: 1536-dim float vector for a brand mention or aggregated brand.
        concept_vector: 1536-dim float vector for an intent cluster centroid.

    Returns:
        Float in [0, 1]. Returns 0.0 if either vector is zero-magnitude.
    """
    if len(brand_vector) != len(concept_vector):
        raise ValueError(
            f"Vector dimension mismatch: {len(brand_vector)} vs {len(concept_vector)}"
        )

    dot = sum(a * b for a, b in zip(brand_vector, concept_vector))
    mag_brand = math.sqrt(sum(a * a for a in brand_vector))
    mag_concept = math.sqrt(sum(b * b for b in concept_vector))

    if mag_brand == 0.0 or mag_concept == 0.0:
        return 0.0

    # Cosine similarity can be slightly outside [-1, 1] due to float rounding
    raw = dot / (mag_brand * mag_concept)
    return max(0.0, min(1.0, (raw + 1.0) / 2.0))  # remap [-1,1] → [0,1]


def aggregate_vectors(vectors: list[list[float]]) -> list[float]:
    """Mean-pool a list of embedding vectors into a single representative vector.

    Used to aggregate multiple brand mention vectors into one brand-level vector
    before computing SPS against intent clusters.
    """
    if not vectors:
        raise ValueError("Cannot aggregate empty list of vectors")

    n = len(vectors)
    dim = len(vectors[0])
    result = [0.0] * dim
    for vec in vectors:
        for i, v in enumerate(vec):
            result[i] += v / n
    return result


def score_brand_vs_clusters(
    brand_vector: list[float],
    cluster_vectors: dict[str, list[float]],
) -> dict[str, float]:
    """Score a single brand vector against all intent cluster centroids.

    Args:
        brand_vector: Aggregated 1536-dim brand embedding.
        cluster_vectors: dict of slug → centroid vector.

    Returns:
        dict of slug → SPS score.
    """
    return {
        slug: calculate_sps(brand_vector, centroid)
        for slug, centroid in cluster_vectors.items()
    }


def batch_score_brands(
    brand_vectors: dict[str, list[float]],  # brand_id → aggregated vector
    cluster_vectors: dict[str, list[float]],  # slug → centroid
) -> dict[str, dict[str, float]]:
    """Score all brands against all clusters.

    Args:
        brand_vectors: dict of brand_id → aggregated embedding vector.
        cluster_vectors: dict of cluster_slug → centroid vector.

    Returns:
        Nested dict: brand_id → {cluster_slug → SPS score}.
    """
    return {
        brand_id: score_brand_vs_clusters(vec, cluster_vectors)
        for brand_id, vec in brand_vectors.items()
    }
