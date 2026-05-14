"""Unit tests for ml/scoring/proximity.py — pure math, no dependencies."""
import math

import pytest

from ml.scoring.proximity import (
    aggregate_vectors,
    batch_score_brands,
    calculate_sps,
    score_brand_vs_clusters,
)

_DIM = 1536


def _unit_vec(dim: int = _DIM, value: float = 1.0) -> list[float]:
    """Return a unit vector (all components equal, normalized)."""
    raw = [value] * dim
    mag = math.sqrt(sum(x * x for x in raw))
    return [x / mag for x in raw]


def _zero_vec(dim: int = _DIM) -> list[float]:
    return [0.0] * dim


def _orthogonal_vec(dim: int = _DIM) -> list[float]:
    """Return a vector orthogonal to _unit_vec."""
    v = [0.0] * dim
    v[0] = 1.0
    v[1] = -1.0
    mag = math.sqrt(2.0)
    return [x / mag for x in v]


class TestCalculateSPS:
    def test_identical_vectors_score_one(self) -> None:
        v = _unit_vec()
        assert calculate_sps(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_opposite_vectors_score_zero(self) -> None:
        v = _unit_vec()
        neg = [-x for x in v]
        # cosine = -1 → remapped to 0
        assert calculate_sps(v, neg) == pytest.approx(0.0, abs=1e-6)

    def test_orthogonal_vectors_score_half(self) -> None:
        """Orthogonal vectors have cosine=0, remapped to 0.5."""
        v1 = [1.0] + [0.0] * (_DIM - 1)
        v2 = [0.0, 1.0] + [0.0] * (_DIM - 2)
        score = calculate_sps(v1, v2)
        assert score == pytest.approx(0.5, abs=1e-6)

    def test_zero_vector_returns_zero(self) -> None:
        v = _unit_vec()
        assert calculate_sps(v, _zero_vec()) == 0.0
        assert calculate_sps(_zero_vec(), v) == 0.0

    def test_score_in_zero_one_range(self) -> None:
        import random
        rng = random.Random(42)
        for _ in range(20):
            a = [rng.gauss(0, 1) for _ in range(_DIM)]
            b = [rng.gauss(0, 1) for _ in range(_DIM)]
            s = calculate_sps(a, b)
            assert 0.0 <= s <= 1.0

    def test_dimension_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="dimension mismatch"):
            calculate_sps([1.0, 0.0], [1.0, 0.0, 0.0])

    def test_symmetry(self) -> None:
        import random
        rng = random.Random(7)
        a = [rng.gauss(0, 1) for _ in range(_DIM)]
        b = [rng.gauss(0, 1) for _ in range(_DIM)]
        assert calculate_sps(a, b) == pytest.approx(calculate_sps(b, a), abs=1e-9)


class TestAggregateVectors:
    def test_single_vector_returned_unchanged(self) -> None:
        v = _unit_vec()
        agg = aggregate_vectors([v])
        assert agg == pytest.approx(v, abs=1e-9)

    def test_two_identical_vectors_aggregate_to_same(self) -> None:
        v = _unit_vec()
        agg = aggregate_vectors([v, v])
        assert agg == pytest.approx(v, abs=1e-9)

    def test_mean_pooling_correctness(self) -> None:
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        agg = aggregate_vectors([v1, v2])
        assert agg == pytest.approx([0.5, 0.5], abs=1e-9)

    def test_empty_list_raises(self) -> None:
        with pytest.raises(ValueError):
            aggregate_vectors([])

    def test_output_dimension_preserved(self) -> None:
        vectors = [[float(i)] * _DIM for i in range(5)]
        agg = aggregate_vectors(vectors)
        assert len(agg) == _DIM


class TestScoreBrandVsClusters:
    def test_returns_score_for_each_cluster(self) -> None:
        brand_vec = _unit_vec()
        clusters = {
            "reliability": _unit_vec(),
            "innovation": _orthogonal_vec(),
        }
        scores = score_brand_vs_clusters(brand_vec, clusters)
        assert set(scores.keys()) == {"reliability", "innovation"}
        assert scores["reliability"] == pytest.approx(1.0, abs=1e-6)
        assert scores["innovation"] == pytest.approx(0.5, abs=0.1)

    def test_empty_clusters_returns_empty_dict(self) -> None:
        assert score_brand_vs_clusters(_unit_vec(), {}) == {}


class TestBatchScoreBrands:
    def test_all_brands_scored_vs_all_clusters(self) -> None:
        import random
        rng = random.Random(99)
        brands = {f"brand-{i}": [rng.gauss(0, 1) for _ in range(_DIM)] for i in range(3)}
        clusters = {f"cluster-{j}": [rng.gauss(0, 1) for _ in range(_DIM)] for j in range(2)}

        result = batch_score_brands(brands, clusters)

        assert set(result.keys()) == set(brands.keys())
        for brand_id, scores in result.items():
            assert set(scores.keys()) == set(clusters.keys())
            for score in scores.values():
                assert 0.0 <= score <= 1.0

    def test_empty_brands_returns_empty_dict(self) -> None:
        clusters = {"reliability": _unit_vec()}
        assert batch_score_brands({}, clusters) == {}
