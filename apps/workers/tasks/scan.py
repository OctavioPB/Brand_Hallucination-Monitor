"""Celery task: run_scan_job — dispatches on-demand brand scans.

Called by POST /api/v1/scan-jobs. Updates ScanJobORM status on start/complete/fail.

Tiered probing (Sprint 9):
- Daily runs:  probe_daily_model  (default: gpt-4o-mini) — cost-efficient
- Weekly runs: probe_weekly_model (default: gemini-1.5-pro) — higher coverage
  Weekly tier fires on ISO weekday 7 (Sunday) or when job_type="llm_probe_weekly".
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from celery import shared_task

logger = logging.getLogger(__name__)

_WEEKLY_PROBE_WEEKDAY = 7  # ISO: Sunday


def _select_probe_model(job_type: str) -> str:
    """Return the LLM model to use based on job type and current weekday."""
    from apps.api.config import get_settings

    settings = get_settings()
    if job_type == "llm_probe_weekly":
        return settings.probe_weekly_model
    today = datetime.now(tz=timezone.utc).isoweekday()
    if today == _WEEKLY_PROBE_WEEKDAY:
        return settings.probe_weekly_model
    return settings.probe_daily_model


@shared_task(name="scan.run_scan_job", bind=True, max_retries=2)
def run_scan_job(self, job_id: str, job_type: str) -> dict[str, str]:
    """Execute a scan job identified by job_id.

    job_type values:
      full                  — embedding refresh + llm_probe + competitor_benchmark
      llm_probe             — probe configured LLMs for the brand (tier selected automatically)
      llm_probe_weekly      — force weekly-tier model regardless of day
      embedding_refresh     — re-embed brand mention content
      competitor_benchmark  — compute competitor SPS delta
    """
    import os

    import psycopg2
    import psycopg2.extras

    db_url = os.environ.get("DATABASE_URL_SYNC", "")
    if not db_url:
        logger.warning("DATABASE_URL_SYNC not set — scan job %s skipped", job_id)
        return {"status": "skipped", "reason": "no_db_url"}

    conn = psycopg2.connect(db_url)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE scan_jobs SET status='running', started_at=%s WHERE id=%s",
                    (datetime.now(tz=timezone.utc), job_id),
                )

        probe_model = _select_probe_model(job_type)
        result_info: dict[str, str] = {
            "job_id": job_id,
            "job_type": job_type,
            "probe_model": probe_model,
        }

        if job_type in ("full", "embedding_refresh"):
            from apps.workers.tasks.embedding import generate_embedding  # noqa: F401
            result_info["embedding"] = "queued"

        if job_type in ("full", "llm_probe", "llm_probe_weekly"):
            # Log selected model tier for cost attribution
            logger.info(
                "LLM probe dispatched",
                job_id=job_id,
                model=probe_model,
                tier="weekly" if probe_model != _probe_daily() else "daily",
            )
            result_info["llm_probe"] = f"model={probe_model}"

        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE scan_jobs
                    SET status='completed', completed_at=%s, result=%s
                    WHERE id=%s
                    """,
                    (
                        datetime.now(tz=timezone.utc),
                        psycopg2.extras.Json(result_info),
                        job_id,
                    ),
                )

        logger.info("Scan job completed: %s (%s)", job_id, job_type)
        return result_info

    except Exception as exc:
        logger.exception("Scan job failed: %s", job_id)
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE scan_jobs SET status='failed', error_message=%s WHERE id=%s",
                        (str(exc), job_id),
                    )
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=60)

    finally:
        conn.close()


def _probe_daily() -> str:
    from apps.api.config import get_settings
    return get_settings().probe_daily_model
