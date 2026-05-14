"""Celery application factory.

Tasks are defined in submodules (e.g., tasks/embedding.py) and registered
via autodiscover_tasks. All I/O-bound tasks use async-to-sync bridging via
asyncio.run() — never block the event loop directly inside a task.
"""
import os

from celery import Celery

from apps.api.config import get_settings

settings = get_settings()

celery_app = Celery(
    "hallucin8",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["apps.workers.tasks.embedding"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)


if __name__ == "__main__":
    celery_app.start()
