"""Airflow DAG: send D+3 and D+7 onboarding emails.

Runs daily at 09:00 UTC. Checks which orgs signed up 3 or 7 days ago
and sends the corresponding email in the sequence.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)

_DEFAULT_ARGS = {
    "owner": "hallucin8",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://hallucin8:hallucin8@postgres:5432/hallucin8",
)


def _send_sequence_emails(**context: object) -> None:
    """Query DB for orgs at D+3 or D+7 and send corresponding emails."""
    import psycopg2
    from urllib.parse import urlparse

    url = urlparse(DATABASE_URL_SYNC.replace("postgresql+psycopg2://", "postgresql://"))
    conn = psycopg2.connect(
        host=url.hostname,
        port=url.port or 5432,
        dbname=url.path.lstrip("/"),
        user=url.username,
        password=url.password,
    )

    today = datetime.utcnow().date()
    d3_date = today - timedelta(days=3)
    d7_date = today - timedelta(days=7)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT email, name
            FROM organizations
            WHERE DATE(created_at) IN (%s, %s)
              AND is_demo = FALSE
            """,
            (d3_date, d7_date),
        )
        rows = cur.fetchall()

    conn.close()

    from apps.api.services.onboarding_emails import send_d3_email, send_d7_email

    for email, name in rows:
        signup_date = None
        # Re-query to get exact date for this email
        conn2 = psycopg2.connect(
            host=url.hostname,
            port=url.port or 5432,
            dbname=url.path.lstrip("/"),
            user=url.username,
            password=url.password,
        )
        with conn2.cursor() as cur:
            cur.execute(
                "SELECT DATE(created_at) FROM organizations WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()
            if row:
                signup_date = row[0]
        conn2.close()

        if signup_date == d3_date:
            log.info("Sending D+3 email to %s", email)
            asyncio.run(send_d3_email(email))
        elif signup_date == d7_date:
            log.info("Sending D+7 email to %s", email)
            asyncio.run(send_d7_email(email))


with DAG(
    dag_id="dag_onboarding_emails",
    description="Send D+3 and D+7 onboarding email sequences to new orgs",
    schedule_interval="0 9 * * *",
    start_date=datetime(2026, 5, 1),
    catchup=False,
    default_args=_DEFAULT_ARGS,
    tags=["onboarding", "email"],
) as dag:
    send_emails = PythonOperator(
        task_id="send_sequence_emails",
        python_callable=_send_sequence_emails,
    )
