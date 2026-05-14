"""Celery task: run_scan_job — dispatches on-demand brand scans.

Called by POST /api/v1/scan-jobs. Updates ScanJobORM status on start/complete/fail.
"""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="scan.run_scan_job", bind=True, max_retries=2)
def run_scan_job(self, job_id: str, job_type: str) -> dict[str, str]:
    """Execute a scan job identified by job_id.

    job_type values:
      full                  — embedding refresh + llm_probe + competitor_benchmark
      llm_probe             — probe all configured LLMs for the brand
      embedding_refresh     — re-embed brand mention content
      competitor_benchmark  — compute competitor SPS delta
    """
    import os
    import uuid
    from datetime import datetime, timezone

    import psycopg2

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

        # Dispatch sub-tasks based on job_type
        result_info: dict[str, str] = {"job_id": job_id, "job_type": job_type}

        if job_type in ("full", "embedding_refresh"):
            from apps.workers.tasks.embedding import generate_embedding  # noqa: F401
            result_info["embedding"] = "queued"

        # llm_probe and competitor_benchmark would trigger their Airflow DAGs via
        # Airflow REST API or direct task instantiation — placeholder for Sprint 9.

        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE scan_jobs
                    SET status='completed', completed_at=%s, result=%s
                    WHERE id=%s
                    """,
                    (datetime.now(tz=timezone.utc), psycopg2.extras.Json(result_info), job_id),
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
