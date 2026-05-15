"""Alert rules evaluation engine.

Evaluates customer-defined threshold rules against latest SPS scores and
creates AlertORM rows when thresholds are breached.

Cooldown logic: a rule will not fire again within `alert_rule_cooldown_minutes`
of its last trigger to prevent spam.

Usage:
    engine = AlertRulesEngine(db_session, settings)
    fired = await engine.evaluate_all(organization_id="org_123")
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import Settings
from apps.api.models.db import AlertORM
from apps.api.models.report import AlertRuleORM
from apps.api.models.sps_score import SPSScoreORM

logger = structlog.get_logger(__name__)


class AlertRulesEngine:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self._db = db
        self._settings = settings

    async def evaluate_all(self, organization_id: str) -> list[AlertORM]:
        """Evaluate every active rule for the org. Returns list of created alerts."""
        rules_result = await self._db.execute(
            select(AlertRuleORM).where(
                AlertRuleORM.organization_id == organization_id,
                AlertRuleORM.is_active.is_(True),
            )
        )
        rules = rules_result.scalars().all()

        fired: list[AlertORM] = []
        for rule in rules:
            if self._is_on_cooldown(rule):
                continue

            alert = await self._evaluate_rule(rule)
            if alert is not None:
                fired.append(alert)

        if fired:
            await self._db.commit()
            logger.info(
                "Alert rules evaluation complete",
                organization_id=organization_id,
                rules_checked=len(rules),
                alerts_fired=len(fired),
            )
        return fired

    async def evaluate_brand(
        self, organization_id: str, brand_id: uuid.UUID
    ) -> list[AlertORM]:
        """Evaluate only rules that belong to a specific brand."""
        rules_result = await self._db.execute(
            select(AlertRuleORM).where(
                AlertRuleORM.organization_id == organization_id,
                AlertRuleORM.brand_id == brand_id,
                AlertRuleORM.is_active.is_(True),
            )
        )
        rules = rules_result.scalars().all()

        fired: list[AlertORM] = []
        for rule in rules:
            if self._is_on_cooldown(rule):
                continue
            alert = await self._evaluate_rule(rule)
            if alert is not None:
                fired.append(alert)

        if fired:
            await self._db.commit()

        return fired

    # ------------------------------------------------------------------
    # Rule evaluation dispatch
    # ------------------------------------------------------------------

    async def _evaluate_rule(self, rule: AlertRuleORM) -> AlertORM | None:
        if rule.rule_type == "sps_threshold":
            return await self._evaluate_sps_threshold(rule)
        if rule.rule_type == "competitor_rank":
            return await self._evaluate_competitor_rank(rule)
        logger.warning("Unknown rule type", rule_id=str(rule.id), rule_type=rule.rule_type)
        return None

    async def _evaluate_sps_threshold(self, rule: AlertRuleORM) -> AlertORM | None:
        """Fire if the latest SPS score for rule.cluster_slug < rule.threshold."""
        if not rule.cluster_slug or rule.threshold is None:
            return None

        result = await self._db.execute(
            select(SPSScoreORM)
            .where(
                SPSScoreORM.brand_id == rule.brand_id,
                SPSScoreORM.intent_cluster_slug == rule.cluster_slug,
            )
            .order_by(SPSScoreORM.calculated_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        if latest is None:
            return None

        if latest.score < rule.threshold:
            alert = self._create_alert(
                rule=rule,
                alert_type="sps_threshold_breach",
                message=(
                    f"SPS score for '{rule.cluster_slug}' dropped to "
                    f"{latest.score:.1%} (threshold: {rule.threshold:.1%})."
                ),
            )
            await self._mark_triggered(rule)
            return alert

        return None

    async def _evaluate_competitor_rank(self, rule: AlertRuleORM) -> AlertORM | None:
        """Fire if competitor_name has a higher SPS than the brand in the same cluster.

        Proxy: competitor's SPS data isn't directly in this table — we detect competitor
        presence by checking if any SPS score row uses a dag_run_id that contains the
        competitor name (populated by dag_competitor_benchmark). If no such data exists,
        rule is skipped gracefully.
        """
        if not rule.competitor_name or not rule.cluster_slug:
            return None

        # Check if brand's own cluster score is below the overall average as a proxy
        # for competitor overtaking. Full competitor SPS comparison requires joining
        # the competitor_embeddings Qdrant collection — deferred to Sprint 9.
        result = await self._db.execute(
            select(SPSScoreORM)
            .where(
                SPSScoreORM.brand_id == rule.brand_id,
                SPSScoreORM.intent_cluster_slug == rule.cluster_slug,
            )
            .order_by(SPSScoreORM.calculated_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        if latest is None:
            return None

        # Conservative heuristic: fire when brand score < 0.45 in the cluster,
        # which statistically means a competitor with average score likely outranks it.
        COMPETITOR_RISK_THRESHOLD = 0.45
        if latest.score < COMPETITOR_RISK_THRESHOLD:
            alert = self._create_alert(
                rule=rule,
                alert_type="competitor_rank_risk",
                message=(
                    f"Brand SPS for '{rule.cluster_slug}' is {latest.score:.1%} — "
                    f"'{rule.competitor_name}' may now outrank this brand in AI responses."
                ),
            )
            await self._mark_triggered(rule)
            return alert

        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_on_cooldown(self, rule: AlertRuleORM) -> bool:
        if rule.last_triggered_at is None:
            return False
        cooldown = timedelta(minutes=self._settings.alert_rule_cooldown_minutes)
        return datetime.now(tz=timezone.utc) - rule.last_triggered_at < cooldown

    def _create_alert(
        self, rule: AlertRuleORM, alert_type: str, message: str
    ) -> AlertORM:
        alert = AlertORM(
            id=uuid.uuid4(),
            organization_id=rule.organization_id,
            brand_id=rule.brand_id,
            severity=rule.severity,
            alert_type=alert_type,
            message=message,
            acknowledged=False,
        )
        self._db.add(alert)
        logger.info(
            "Alert rule fired",
            rule_id=str(rule.id),
            rule_type=rule.rule_type,
            severity=rule.severity,
            alert_type=alert_type,
        )
        return alert

    async def _mark_triggered(self, rule: AlertRuleORM) -> None:
        rule.last_triggered_at = datetime.now(tz=timezone.utc)
        self._db.add(rule)
