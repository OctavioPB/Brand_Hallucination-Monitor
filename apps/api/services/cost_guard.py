"""CostGuard — daily budget cap enforcement for external API calls.

Queries the embedding_costs table to compute today's total spend per
organization, and raises BudgetExceededError before any API call that would
push spend over the configured limit.

Design decisions:
- Sync (psycopg2) so it can be called from both Celery workers and Airflow tasks
  without an event loop.
- Org-scoped: each organization has its own daily budget drawn from the same
  global max_daily_spend_usd setting (per-org customization is a Sprint 10 item).
- Fail-open: if the DB is unavailable the guard lets the call through rather than
  blocking all embeddings — the budget protection is best-effort, not hard-stop.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal

logger = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    """Raised when an org's daily API spend would exceed the configured cap."""

    def __init__(self, org_id: str, spent: float, cap: float) -> None:
        self.org_id = org_id
        self.spent = spent
        self.cap = cap
        super().__init__(
            f"Daily budget exceeded for org {org_id}: "
            f"${spent:.4f} spent of ${cap:.2f} cap"
        )


class CostGuard:
    """Check daily spend and raise BudgetExceededError if cap is reached."""

    def __init__(self, db_url: str, max_daily_spend_usd: float) -> None:
        self._db_url = db_url
        self._cap = Decimal(str(max_daily_spend_usd))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def check_budget(self, org_id: str, estimated_cost_usd: float = 0.0) -> None:
        """Raise BudgetExceededError if today's spend + estimate exceeds cap.

        Args:
            org_id: The organization whose budget to check.
            estimated_cost_usd: Additional cost about to be incurred.
        """
        today_spend = self._get_today_spend(org_id)
        projected = today_spend + Decimal(str(estimated_cost_usd))
        if projected > self._cap:
            raise BudgetExceededError(
                org_id=org_id,
                spent=float(today_spend),
                cap=float(self._cap),
            )

    def get_daily_summary(self, org_id: str | None = None) -> dict[str, object]:
        """Return today's spend summary, optionally filtered by org."""
        try:
            import psycopg2

            conn = psycopg2.connect(self._db_url)
            today = date.today().isoformat()
            with conn:
                with conn.cursor() as cur:
                    if org_id:
                        cur.execute(
                            """
                            SELECT
                                COALESCE(SUM(cost_usd)::numeric, 0) AS total,
                                COUNT(*) AS calls,
                                COALESCE(SUM(tokens_input), 0) AS tokens,
                                COALESCE(SUM(n_cached), 0) AS cached_vectors
                            FROM embedding_costs
                            WHERE DATE(logged_at) = %s
                              AND org_id = %s
                            """,
                            (today, org_id),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT
                                COALESCE(SUM(cost_usd)::numeric, 0) AS total,
                                COUNT(*) AS calls,
                                COALESCE(SUM(tokens_input), 0) AS tokens,
                                COALESCE(SUM(n_cached), 0) AS cached_vectors
                            FROM embedding_costs
                            WHERE DATE(logged_at) = %s
                            """,
                            (today,),
                        )
                    row = cur.fetchone()
            conn.close()
            total, calls, tokens, cached = row or (0, 0, 0, 0)
            return {
                "date": today,
                "total_cost_usd": float(total),
                "budget_cap_usd": float(self._cap),
                "budget_remaining_usd": max(0.0, float(self._cap) - float(total)),
                "budget_used_pct": round(
                    float(total) / float(self._cap) * 100, 1
                ) if float(self._cap) > 0 else 0.0,
                "api_calls": calls,
                "tokens_consumed": tokens,
                "vectors_from_cache": cached,
                "computed_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        except Exception:
            logger.exception("CostGuard.get_daily_summary failed")
            return {"error": "unavailable"}

    def get_monthly_breakdown(self, limit: int = 30) -> list[dict[str, object]]:
        """Return per-brand per-day cost breakdown for the past `limit` days."""
        try:
            import psycopg2

            conn = psycopg2.connect(self._db_url)
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            DATE(logged_at) AS day,
                            org_id,
                            job_type,
                            SUM(cost_usd)::numeric AS cost_usd,
                            SUM(tokens_input) AS tokens,
                            COUNT(*) AS calls
                        FROM embedding_costs
                        WHERE logged_at >= NOW() - INTERVAL '%s days'
                        GROUP BY DATE(logged_at), org_id, job_type
                        ORDER BY day DESC, cost_usd DESC
                        """,
                        (limit,),
                    )
                    rows = cur.fetchall()
            conn.close()
            return [
                {
                    "day": str(r[0]),
                    "org_id": r[1],
                    "job_type": r[2],
                    "cost_usd": float(r[3]),
                    "tokens": r[4],
                    "calls": r[5],
                }
                for r in rows
            ]
        except Exception:
            logger.exception("CostGuard.get_monthly_breakdown failed")
            return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_today_spend(self, org_id: str) -> Decimal:
        try:
            import psycopg2

            conn = psycopg2.connect(self._db_url)
            today = date.today().isoformat()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COALESCE(SUM(cost_usd)::numeric, 0)
                        FROM embedding_costs
                        WHERE DATE(logged_at) = %s
                          AND org_id = %s
                        """,
                        (today, org_id),
                    )
                    result = cur.fetchone()
            conn.close()
            return Decimal(str(result[0])) if result else Decimal("0")
        except Exception:
            logger.warning(
                "CostGuard: DB unavailable — budget check skipped",
                org_id=org_id,
            )
            return Decimal("0")
