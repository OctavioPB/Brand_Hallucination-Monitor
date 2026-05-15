"""Unit tests for AlertRulesEngine."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.services.alert_rules import AlertRulesEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_settings(cooldown_minutes: int = 60) -> MagicMock:
    s = MagicMock()
    s.alert_rule_cooldown_minutes = cooldown_minutes
    return s


def _make_rule(
    rule_type: str = "sps_threshold",
    cluster_slug: str | None = "reliability",
    threshold: float | None = 0.6,
    competitor_name: str | None = None,
    severity: str = "HIGH",
    last_triggered_at: datetime | None = None,
) -> MagicMock:
    rule = MagicMock()
    rule.id = uuid.uuid4()
    rule.organization_id = "org_123"
    rule.brand_id = uuid.uuid4()
    rule.rule_type = rule_type
    rule.cluster_slug = cluster_slug
    rule.threshold = threshold
    rule.competitor_name = competitor_name
    rule.severity = severity
    rule.is_active = True
    rule.last_triggered_at = last_triggered_at
    return rule


def _make_sps_row(score: float, slug: str = "reliability") -> MagicMock:
    from apps.api.models.sps_score import SPSScoreORM

    row = MagicMock(spec=SPSScoreORM)
    row.score = score
    row.intent_cluster_slug = slug
    row.calculated_at = datetime.now(tz=timezone.utc)
    return row


def _make_db_with_sps(score: float) -> AsyncMock:
    """Return an AsyncSession mock that returns one SPS row with the given score."""
    sps_row = _make_sps_row(score)
    scalars = MagicMock()
    scalars.scalar_one_or_none = MagicMock(return_value=sps_row)

    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=sps_row)
    execute_result.scalars = MagicMock(return_value=scalars)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=execute_result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


def _make_db_no_sps() -> AsyncMock:
    """Return a mock DB that returns no SPS rows."""
    execute_result = MagicMock()
    execute_result.scalar_one_or_none = MagicMock(return_value=None)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=execute_result)
    return db


# ---------------------------------------------------------------------------
# Cooldown logic
# ---------------------------------------------------------------------------

class TestCooldown:
    def test_not_on_cooldown_if_never_triggered(self) -> None:
        engine = AlertRulesEngine(AsyncMock(), _make_settings())
        rule = _make_rule(last_triggered_at=None)
        assert engine._is_on_cooldown(rule) is False

    def test_on_cooldown_within_window(self) -> None:
        engine = AlertRulesEngine(AsyncMock(), _make_settings(cooldown_minutes=60))
        rule = _make_rule(
            last_triggered_at=datetime.now(tz=timezone.utc) - timedelta(minutes=30)
        )
        assert engine._is_on_cooldown(rule) is True

    def test_not_on_cooldown_after_window_expires(self) -> None:
        engine = AlertRulesEngine(AsyncMock(), _make_settings(cooldown_minutes=60))
        rule = _make_rule(
            last_triggered_at=datetime.now(tz=timezone.utc) - timedelta(minutes=90)
        )
        assert engine._is_on_cooldown(rule) is False


# ---------------------------------------------------------------------------
# sps_threshold evaluation
# ---------------------------------------------------------------------------

class TestSPSThreshold:
    @pytest.mark.asyncio
    async def test_fires_when_score_below_threshold(self) -> None:
        rule = _make_rule(rule_type="sps_threshold", cluster_slug="reliability", threshold=0.60)
        db = _make_db_with_sps(0.45)  # below threshold
        engine = AlertRulesEngine(db, _make_settings())

        alert = await engine._evaluate_sps_threshold(rule)
        assert alert is not None
        assert alert.severity == "HIGH"
        assert "reliability" in alert.message
        assert "0.45" in alert.message or "45" in alert.message

    @pytest.mark.asyncio
    async def test_no_alert_when_score_above_threshold(self) -> None:
        rule = _make_rule(rule_type="sps_threshold", cluster_slug="reliability", threshold=0.60)
        db = _make_db_with_sps(0.75)  # above threshold
        engine = AlertRulesEngine(db, _make_settings())

        alert = await engine._evaluate_sps_threshold(rule)
        assert alert is None

    @pytest.mark.asyncio
    async def test_no_alert_when_no_sps_data(self) -> None:
        rule = _make_rule(rule_type="sps_threshold", cluster_slug="reliability", threshold=0.60)
        db = _make_db_no_sps()
        engine = AlertRulesEngine(db, _make_settings())

        alert = await engine._evaluate_sps_threshold(rule)
        assert alert is None

    @pytest.mark.asyncio
    async def test_skips_rule_missing_cluster_or_threshold(self) -> None:
        engine = AlertRulesEngine(AsyncMock(), _make_settings())
        rule_no_cluster = _make_rule(cluster_slug=None, threshold=0.6)
        assert await engine._evaluate_sps_threshold(rule_no_cluster) is None

        rule_no_threshold = _make_rule(cluster_slug="reliability", threshold=None)
        assert await engine._evaluate_sps_threshold(rule_no_threshold) is None

    @pytest.mark.asyncio
    async def test_alert_type_is_sps_threshold_breach(self) -> None:
        rule = _make_rule(threshold=0.60)
        db = _make_db_with_sps(0.50)
        engine = AlertRulesEngine(db, _make_settings())

        alert = await engine._evaluate_sps_threshold(rule)
        assert alert is not None
        assert alert.alert_type == "sps_threshold_breach"


# ---------------------------------------------------------------------------
# evaluate_all — integration across multiple rules
# ---------------------------------------------------------------------------

class TestEvaluateAll:
    @pytest.mark.asyncio
    async def test_skips_rules_on_cooldown(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()

        # Rules result
        rule_on_cooldown = _make_rule(
            last_triggered_at=datetime.now(tz=timezone.utc) - timedelta(minutes=10)
        )
        rules_scalars = MagicMock()
        rules_scalars.all = MagicMock(return_value=[rule_on_cooldown])
        rules_exec = MagicMock()
        rules_exec.scalars = MagicMock(return_value=rules_scalars)
        db.execute = AsyncMock(return_value=rules_exec)

        engine = AlertRulesEngine(db, _make_settings(cooldown_minutes=60))
        fired = await engine.evaluate_all("org_123")
        assert fired == []

    @pytest.mark.asyncio
    async def test_unknown_rule_type_is_skipped(self) -> None:
        rule = _make_rule(rule_type="unknown_type", last_triggered_at=None)

        rules_scalars = MagicMock()
        rules_scalars.all = MagicMock(return_value=[rule])
        rules_exec = MagicMock()
        rules_exec.scalars = MagicMock(return_value=rules_scalars)

        db = AsyncMock()
        db.execute = AsyncMock(return_value=rules_exec)
        db.commit = AsyncMock()

        engine = AlertRulesEngine(db, _make_settings())
        fired = await engine.evaluate_all("org_123")
        assert fired == []
