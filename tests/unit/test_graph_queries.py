"""Unit tests for graph/queries.py — mock Neo4j driver, verify query contracts."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from apps.api.graph.queries import (
    AssociationWrite,
    ClusterRanking,
    CompetitorConceptScore,
    CompetitorProximity,
    ConceptAssociation,
    HallucinationRecord,
    get_brand_concept_associations,
    get_competitor_proximity_map,
    get_hallucination_history,
    get_intent_cluster_ranking,
    write_associations_batch,
)


def _make_client(return_rows: list[dict]) -> MagicMock:
    """Return a Neo4jClient mock whose .run() returns the given rows."""
    client = MagicMock()
    client.run.return_value = return_rows
    client.run_write_batch.return_value = len(return_rows)
    return client


class TestGetBrandConceptAssociations:
    def test_returns_typed_list(self) -> None:
        rows = [
            {
                "concept_slug": "uptime_guarantee",
                "concept_name": "Uptime Guarantee",
                "score": 0.87,
                "source": "embedding_batch",
                "timestamp": "2026-05-14T12:00:00",
                "cluster_slug": "reliability",
            }
        ]
        client = _make_client(rows)
        result = get_brand_concept_associations(client, "brand-001", limit=20)

        assert len(result) == 1
        assert isinstance(result[0], ConceptAssociation)
        assert result[0].concept_slug == "uptime_guarantee"
        assert result[0].score == pytest.approx(0.87)
        assert result[0].cluster_slug == "reliability"

    def test_passes_brand_id_and_limit_as_params(self) -> None:
        client = _make_client([])
        get_brand_concept_associations(client, "brand-xyz", limit=5)

        call_kwargs = client.run.call_args
        assert call_kwargs[1]["brand_id"] == "brand-xyz"
        assert call_kwargs[1]["limit"] == 5

    def test_empty_result_returns_empty_list(self) -> None:
        client = _make_client([])
        result = get_brand_concept_associations(client, "brand-001")
        assert result == []

    def test_score_clamped_within_zero_one(self) -> None:
        """Scores from the DB should always be in [0,1] — verify no crash on edge values."""
        rows = [
            {
                "concept_slug": "edge",
                "concept_name": "Edge",
                "score": 1.0,
                "source": "test",
                "timestamp": None,
                "cluster_slug": None,
            }
        ]
        client = _make_client(rows)
        result = get_brand_concept_associations(client, "b")
        assert result[0].score == pytest.approx(1.0)

    def test_no_string_interpolation_in_query(self) -> None:
        """The query string must NOT contain f-string or .format() patterns."""
        from apps.api.graph.queries import _BRAND_CONCEPT_ASSOCIATIONS
        assert "$brand_id" in _BRAND_CONCEPT_ASSOCIATIONS
        assert "$limit" in _BRAND_CONCEPT_ASSOCIATIONS
        # No sign of string interpolation
        assert "{brand_id}" not in _BRAND_CONCEPT_ASSOCIATIONS
        assert "%" + "s" not in _BRAND_CONCEPT_ASSOCIATIONS


class TestGetCompetitorProximityMap:
    def test_returns_competitor_list(self) -> None:
        rows = [
            {
                "competitor_id": "comp-001",
                "competitor_name": "BetaTech",
                "market_segment": "enterprise_saas",
                "concept_scores": [
                    {"concept_slug": "api_first", "score": 0.77},
                ],
            }
        ]
        client = _make_client(rows)
        result = get_competitor_proximity_map(client, "brand-001")

        assert len(result) == 1
        assert isinstance(result[0], CompetitorProximity)
        assert result[0].competitor_name == "BetaTech"
        assert result[0].market_segment == "enterprise_saas"
        assert len(result[0].concept_scores) == 1
        assert result[0].concept_scores[0].concept_slug == "api_first"

    def test_empty_concept_scores_handled(self) -> None:
        rows = [
            {
                "competitor_id": "comp-002",
                "competitor_name": "NoScores",
                "market_segment": None,
                "concept_scores": [],
            }
        ]
        client = _make_client(rows)
        result = get_competitor_proximity_map(client, "brand-001")
        assert result[0].concept_scores == []

    def test_null_concept_scores_in_row_handled(self) -> None:
        rows = [
            {
                "competitor_id": "comp-003",
                "competitor_name": "NullScores",
                "market_segment": None,
                "concept_scores": None,
            }
        ]
        client = _make_client(rows)
        result = get_competitor_proximity_map(client, "brand-001")
        assert result[0].concept_scores == []

    def test_brand_id_passed_as_param(self) -> None:
        client = _make_client([])
        get_competitor_proximity_map(client, "target-brand")
        assert client.run.call_args[1]["brand_id"] == "target-brand"


class TestGetHallucinationHistory:
    def test_returns_typed_records(self) -> None:
        rows = [
            {
                "attribute_slug": "founded_pre_2010",
                "attribute_text": "Founded before 2010",
                "polarity": "neutral",
                "model": "gpt-4o",
                "confidence": 0.76,
                "detected_at": "2026-05-14T10:00:00",
            }
        ]
        client = _make_client(rows)
        result = get_hallucination_history(client, "brand-001")

        assert len(result) == 1
        assert isinstance(result[0], HallucinationRecord)
        assert result[0].model == "gpt-4o"
        assert result[0].confidence == pytest.approx(0.76)

    def test_model_name_filter_passed_as_param(self) -> None:
        client = _make_client([])
        get_hallucination_history(client, "brand-001", model_name="gemini-1.5-pro")
        assert client.run.call_args[1]["model_name"] == "gemini-1.5-pro"

    def test_empty_model_name_passes_empty_string(self) -> None:
        client = _make_client([])
        get_hallucination_history(client, "brand-001")
        assert client.run.call_args[1]["model_name"] == ""

    def test_no_cypher_injection_in_query(self) -> None:
        from apps.api.graph.queries import _HALLUCINATION_HISTORY
        assert "$brand_id" in _HALLUCINATION_HISTORY
        assert "$model_name" in _HALLUCINATION_HISTORY


class TestGetIntentClusterRanking:
    def test_returns_cluster_rankings(self) -> None:
        rows = [
            {"cluster_slug": "reliability", "cluster_name": "Reliability & Trust",
             "avg_score": 0.87, "concept_count": 4},
            {"cluster_slug": "innovation", "cluster_name": "Innovation & Technology",
             "avg_score": 0.72, "concept_count": 3},
        ]
        client = _make_client(rows)
        result = get_intent_cluster_ranking(client, "brand-001")

        assert len(result) == 2
        assert isinstance(result[0], ClusterRanking)
        assert result[0].cluster_slug == "reliability"
        assert result[0].avg_score == pytest.approx(0.87)
        assert result[1].avg_score < result[0].avg_score

    def test_concept_count_is_int(self) -> None:
        rows = [{"cluster_slug": "s", "cluster_name": "S", "avg_score": 0.5, "concept_count": 2}]
        client = _make_client(rows)
        result = get_intent_cluster_ranking(client, "b")
        assert isinstance(result[0].concept_count, int)


class TestWriteAssociationsBatch:
    def test_calls_run_write_batch_with_rows(self) -> None:
        client = MagicMock()
        client.run_write_batch.return_value = 2

        assocs = [
            AssociationWrite(
                brand_id="brand-001",
                brand_name="AcmeCorp",
                brand_slug="acmecorp",
                organization_id="org-001",
                concept_slug="reliability",
                concept_display_name="Reliability",
                score=0.85,
                source="embedding_batch",
                timestamp="2026-05-14T12:00:00+00:00",
            ),
            AssociationWrite(
                brand_id="brand-001",
                brand_name="AcmeCorp",
                brand_slug="acmecorp",
                organization_id="org-001",
                concept_slug="innovation",
                concept_display_name="Innovation",
                score=0.73,
                source="embedding_batch",
                timestamp="2026-05-14T12:00:00+00:00",
            ),
        ]

        result = write_associations_batch(client, assocs)
        assert result == 2
        client.run_write_batch.assert_called_once()
        # First arg is the query string, second kwarg is rows
        call_args = client.run_write_batch.call_args
        assert "UNWIND $rows AS row" in call_args[0][0]
        assert len(call_args[1]["rows"]) == 2

    def test_empty_list_returns_zero_without_db_call(self) -> None:
        client = MagicMock()
        result = write_associations_batch(client, [])
        assert result == 0
        client.run_write_batch.assert_not_called()

    def test_association_write_score_validation(self) -> None:
        """Score must be in [0, 1]."""
        with pytest.raises(Exception):
            AssociationWrite(
                brand_id="b",
                brand_name="B",
                brand_slug="b",
                organization_id="o",
                concept_slug="c",
                concept_display_name="C",
                score=1.5,  # invalid
                source="test",
                timestamp="2026-05-14T12:00:00+00:00",
            )

    def test_write_query_uses_parameterized_merge(self) -> None:
        """Verify the UNWIND write query uses $rows not string formatting."""
        from apps.api.graph.queries import _WRITE_ASSOCIATIONS_BATCH
        assert "UNWIND $rows AS row" in _WRITE_ASSOCIATIONS_BATCH
        assert "MERGE (b:Brand {brand_id: row.brand_id})" in _WRITE_ASSOCIATIONS_BATCH
        # Must not contain Python string interpolation markers
        assert "{brand_id}" not in _WRITE_ASSOCIATIONS_BATCH
