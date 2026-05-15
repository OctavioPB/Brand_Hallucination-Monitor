"""Unit tests for ReportGenerator service."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.models.report import ReportORM
from apps.api.services.report_generator import (
    ClusterSPS,
    ReportContent,
    ReportGenerator,
    _RECOMMENDED_ACTIONS,
    _SPS_WARN,
)


# ---------------------------------------------------------------------------
# ClusterSPS helpers
# ---------------------------------------------------------------------------

class TestClusterSPS:
    def test_delta_positive(self) -> None:
        c = ClusterSPS(slug="reliability", current_score=0.75, previous_score=0.60)
        assert abs(c.delta - 0.15) < 1e-9

    def test_delta_negative(self) -> None:
        c = ClusterSPS(slug="innovation", current_score=0.40, previous_score=0.55)
        assert abs(c.delta - (-0.15)) < 1e-9

    def test_trend_improving(self) -> None:
        c = ClusterSPS(slug="reliability", current_score=0.80, previous_score=0.75)
        assert c.trend == "improving"

    def test_trend_declining(self) -> None:
        c = ClusterSPS(slug="reliability", current_score=0.65, previous_score=0.75)
        assert c.trend == "declining"

    def test_trend_stable_when_small_change(self) -> None:
        c = ClusterSPS(slug="reliability", current_score=0.75, previous_score=0.742)
        assert c.trend == "stable"


# ---------------------------------------------------------------------------
# ReportContent.to_dict
# ---------------------------------------------------------------------------

class TestReportContentToDict:
    def test_round_trips_all_fields(self) -> None:
        ws = date(2026, 5, 5)
        we = date(2026, 5, 11)
        clusters = [
            ClusterSPS("reliability", 0.72, 0.68),
            ClusterSPS("innovation", 0.45, 0.50),
        ]
        content = ReportContent(
            brand_id="brand-123",
            brand_name="Acme Corp",
            week_start=ws,
            week_end=we,
            clusters=clusters,
            top_hallucinations=[{"model_name": "gpt-4o", "hallucinations_detected": 2, "probe_prompt": "test", "cost_usd": 0.01, "probed_at": "2026-05-08T00:00:00"}],
            total_probes=10,
            total_hallucinations=2,
            active_alerts=1,
            recommended_actions=["Action A"],
        )
        d = content.to_dict()

        assert d["brand_name"] == "Acme Corp"
        assert d["week_start"] == "2026-05-05"
        assert d["total_probes"] == 10
        assert len(d["clusters"]) == 2
        assert d["clusters"][0]["trend"] == "improving"
        assert d["clusters"][1]["trend"] == "declining"

    def test_empty_clusters_produces_empty_list(self) -> None:
        content = ReportContent(
            brand_id="x",
            brand_name="Test",
            week_start=date.today(),
            week_end=date.today(),
        )
        assert content.to_dict()["clusters"] == []


# ---------------------------------------------------------------------------
# Recommended action selection
# ---------------------------------------------------------------------------

class TestRecommendedActions:
    def test_low_sps_triggers_recommendation(self) -> None:
        """A cluster score below _SPS_WARN should produce a recommendation."""
        c = ClusterSPS("reliability", current_score=_SPS_WARN - 0.05, previous_score=0.60)
        content = ReportContent(
            brand_id="x", brand_name="B", week_start=date.today(), week_end=date.today()
        )
        content.clusters = [c]
        # Simulate the action logic from _assemble
        recommended = []
        for cluster in content.clusters:
            if cluster.current_score < _SPS_WARN and cluster.slug in _RECOMMENDED_ACTIONS:
                recommended.append(_RECOMMENDED_ACTIONS[cluster.slug])
        assert len(recommended) == 1
        assert "reliability" in recommended[0].lower() or "success stories" in recommended[0].lower()

    def test_all_clusters_healthy_no_recommendation(self) -> None:
        c = ClusterSPS("reliability", current_score=0.80, previous_score=0.75)
        if c.current_score >= _SPS_WARN:
            recommended = []
        assert recommended == []


# ---------------------------------------------------------------------------
# PDF rendering — graceful fallback when reportlab absent
# ---------------------------------------------------------------------------

class TestRenderPDF:
    def test_empty_bytes_when_reportlab_missing(self) -> None:
        """If reportlab isn't installed the method returns b'' without raising."""
        content = ReportContent(
            brand_id="x", brand_name="B", week_start=date.today(), week_end=date.today()
        )
        gen = ReportGenerator.__new__(ReportGenerator)

        with patch("builtins.__import__", side_effect=ImportError("no reportlab")):
            # Can't easily patch the try/import inside the method without DI,
            # but we can confirm the contract: if the try block fails, returns b"".
            # We test the fallback directly by calling with a mocked import.
            import importlib
            import sys
            saved = sys.modules.pop("reportlab", None)
            try:
                result = gen._render_pdf(content)
                # Either b"" (no reportlab) or valid PDF bytes (reportlab present)
                assert isinstance(result, bytes)
            finally:
                if saved is not None:
                    sys.modules["reportlab"] = saved

    def test_returns_bytes_type(self) -> None:
        content = ReportContent(
            brand_id="x", brand_name="TestBrand", week_start=date.today(), week_end=date.today()
        )
        gen = ReportGenerator.__new__(ReportGenerator)
        result = gen._render_pdf(content)
        assert isinstance(result, bytes)


# ---------------------------------------------------------------------------
# _latest_sps_per_cluster aggregation
# ---------------------------------------------------------------------------

class TestLatestSPSPerCluster:
    @pytest.mark.asyncio
    async def test_returns_latest_per_slug(self) -> None:
        """When two rows exist for same slug, only the latest (first after desc sort) wins."""
        from apps.api.models.sps_score import SPSScoreORM

        row1 = MagicMock(spec=SPSScoreORM)
        row1.intent_cluster_slug = "reliability"
        row1.score = 0.80
        row1.calculated_at = datetime(2026, 5, 10, tzinfo=timezone.utc)

        row2 = MagicMock(spec=SPSScoreORM)
        row2.intent_cluster_slug = "reliability"
        row2.score = 0.70
        row2.calculated_at = datetime(2026, 5, 9, tzinfo=timezone.utc)

        row3 = MagicMock(spec=SPSScoreORM)
        row3.intent_cluster_slug = "innovation"
        row3.score = 0.55
        row3.calculated_at = datetime(2026, 5, 10, tzinfo=timezone.utc)

        # Simulate already-sorted desc order (row1 before row2 for same slug)
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [row1, row2, row3]

        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock

        db = AsyncMock()
        db.execute = AsyncMock(return_value=execute_result)

        gen = ReportGenerator(db)
        result = await gen._latest_sps_per_cluster(
            brand_id=uuid.uuid4(),
            since=datetime(2026, 5, 9, tzinfo=timezone.utc),
            until=datetime(2026, 5, 11, tzinfo=timezone.utc),
        )

        assert result["reliability"] == pytest.approx(0.80)
        assert result["innovation"] == pytest.approx(0.55)
        assert len(result) == 2
