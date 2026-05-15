"""DAG: dag_weekly_report — weekly brand safety report generation and email delivery.

Schedule: 08:00 UTC every Sunday.
Tasks:
  1. fetch_brands_for_reports — list brands with a manifest from PostgreSQL
  2. generate_reports         — build report JSON + PDF via ReportGenerator
  3. email_reports            — send PDF to org's registered email recipients via Resend
  4. evaluate_alert_rules     — run AlertRulesEngine for all orgs after fresh weekly data
"""
from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from typing import Any

import psycopg2
from airflow.decorators import dag, task
from airflow.utils.dates import days_ago

logger = logging.getLogger(__name__)

_DB_URL = os.environ.get("DATABASE_URL", "")
_RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
_RESEND_FROM = os.environ.get("RESEND_FROM_EMAIL", "reports@hallucin8.io")


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------

@dag(
    dag_id="dag_weekly_report",
    schedule_interval="0 8 * * 0",  # 08:00 UTC every Sunday
    start_date=days_ago(1),
    catchup=False,
    tags=["reports", "alerting", "sprint8"],
    doc_md=__doc__,
)
def dag_weekly_report() -> None:

    # ------------------------------------------------------------------
    # Task 1: fetch_brands_for_reports
    # ------------------------------------------------------------------

    @task()
    def fetch_brands_for_reports() -> list[dict[str, Any]]:
        """Return all brands that have a manifest — these get weekly reports."""
        conn = psycopg2.connect(_DB_URL)
        brands: list[dict[str, Any]] = []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, slug, organization_id
                    FROM brands
                    WHERE manifest IS NOT NULL
                    ORDER BY organization_id, name
                    """
                )
                for row in cur.fetchall():
                    brands.append({
                        "id": str(row[0]),
                        "name": row[1],
                        "slug": row[2],
                        "organization_id": row[3],
                    })
        finally:
            conn.close()

        logger.info("Fetched %d brands for weekly reports", len(brands))
        return brands

    # ------------------------------------------------------------------
    # Task 2: generate_reports
    # ------------------------------------------------------------------

    @task()
    def generate_reports(brands: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate a weekly report for each brand; persist to reports table.

        Returns list of dicts with report_id and organization_id for email task.
        """
        import asyncio
        import uuid as _uuid

        import psycopg2.extras
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from apps.api.services.report_generator import ReportGenerator

        async def _generate_all() -> list[dict[str, Any]]:
            engine = create_async_engine(_DB_URL.replace("postgresql://", "postgresql+asyncpg://").replace("postgresql+asyncpg+psycopg2://", "postgresql+asyncpg://"), echo=False)
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            week_start = date.today() - timedelta(days=7)
            results: list[dict[str, Any]] = []

            async with factory() as session:
                gen = ReportGenerator(session)
                for brand in brands:
                    try:
                        report = await gen.generate_weekly(
                            brand_id=_uuid.UUID(brand["id"]),
                            organization_id=brand["organization_id"],
                            brand_name=brand["name"],
                            week_start=week_start,
                        )
                        results.append({
                            "report_id": str(report.id),
                            "organization_id": brand["organization_id"],
                            "brand_name": brand["name"],
                            "title": report.title,
                            "has_pdf": report.pdf_bytes is not None,
                        })
                        logger.info(
                            "Report generated for %s (%s)",
                            brand["name"],
                            brand["organization_id"],
                        )
                    except Exception:
                        logger.exception("Report generation failed for brand %s", brand["id"])

            await engine.dispose()
            return results

        return asyncio.run(_generate_all())

    # ------------------------------------------------------------------
    # Task 3: email_reports
    # ------------------------------------------------------------------

    @task()
    def email_reports(generated: list[dict[str, Any]]) -> int:
        """Send weekly report emails via Resend API.

        For each report, queries webhook_endpoints with mailto: URLs and sends PDF.
        Returns count of emails sent.
        """
        if not _RESEND_API_KEY:
            logger.info("RESEND_API_KEY not configured — skipping email delivery")
            return 0

        import uuid as _uuid

        import httpx
        import psycopg2

        conn = psycopg2.connect(_DB_URL)
        sent = 0

        try:
            for entry in generated:
                # Fetch email recipients for this org
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT url FROM webhook_endpoints
                        WHERE organization_id = %s
                          AND is_active = true
                          AND url LIKE 'mailto:%%'
                        """,
                        (entry["organization_id"],),
                    )
                    recipients = [row[0][7:] for row in cur.fetchall()]

                if not recipients:
                    continue

                # Fetch PDF bytes
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT pdf_bytes, title FROM reports WHERE id = %s",
                        (_uuid.UUID(entry["report_id"]),),
                    )
                    row = cur.fetchone()

                if row is None or not row[0]:
                    logger.warning("No PDF for report %s — skipping email", entry["report_id"])
                    continue

                pdf_bytes, title = row
                import base64
                pdf_b64 = base64.b64encode(pdf_bytes).decode()

                for recipient in recipients:
                    try:
                        resp = httpx.post(
                            "https://api.resend.com/emails",
                            headers={
                                "Authorization": f"Bearer {_RESEND_API_KEY}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "from": _RESEND_FROM,
                                "to": [recipient],
                                "subject": f"hallucin8 Weekly Report — {title}",
                                "html": (
                                    f"<p>Your weekly brand safety report for "
                                    f"<strong>{entry['brand_name']}</strong> is attached.</p>"
                                    f"<p style='color:#6B7280;font-size:11px'>"
                                    f"hallucin8 — SGE Semantic Dominance</p>"
                                ),
                                "attachments": [
                                    {
                                        "filename": f"{title.replace(' ', '_')}.pdf",
                                        "content": pdf_b64,
                                    }
                                ],
                            },
                            timeout=15.0,
                        )
                        resp.raise_for_status()
                        sent += 1
                        logger.info(
                            "Weekly report emailed",
                            recipient=recipient,
                            report_id=entry["report_id"],
                        )

                        # Update emailed_to on report row
                        with conn:
                            with conn.cursor() as cur:
                                cur.execute(
                                    "UPDATE reports SET emailed_to = %s WHERE id = %s",
                                    (recipient, _uuid.UUID(entry["report_id"])),
                                )
                    except Exception:
                        logger.exception(
                            "Email delivery failed to %s for report %s",
                            recipient,
                            entry["report_id"],
                        )
        finally:
            conn.close()

        logger.info("Email delivery complete: %d emails sent", sent)
        return sent

    # ------------------------------------------------------------------
    # Task 4: evaluate_alert_rules
    # ------------------------------------------------------------------

    @task()
    def evaluate_alert_rules(brands: list[dict[str, Any]]) -> int:
        """Run the alert rules engine for every distinct org in the brand list."""
        import asyncio
        import uuid as _uuid

        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        from apps.api.config import get_settings
        from apps.api.services.alert_rules import AlertRulesEngine

        settings = get_settings()

        async def _evaluate() -> int:
            engine = create_async_engine(
                _DB_URL.replace("postgresql://", "postgresql+asyncpg://"),
                echo=False,
            )
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            # Deduplicate org IDs
            org_ids = {b["organization_id"] for b in brands}
            total_fired = 0

            async with factory() as session:
                rules_engine = AlertRulesEngine(session, settings)
                for org_id in org_ids:
                    fired = await rules_engine.evaluate_all(org_id)
                    total_fired += len(fired)
                    logger.info("Alert rules evaluated for org %s: %d fired", org_id, len(fired))

            await engine.dispose()
            return total_fired

        return asyncio.run(_evaluate())

    # ------------------------------------------------------------------
    # DAG wiring
    # ------------------------------------------------------------------
    brands_data = fetch_brands_for_reports()
    generated = generate_reports(brands_data)
    email_reports(generated)
    evaluate_alert_rules(brands_data)


dag_weekly_report()
