"""Prometheus metrics instrumentation for the FastAPI application.

Exposes:
- Standard HTTP metrics via prometheus-fastapi-instrumentator
  (request count, latency histogram, in-progress gauge — auto-generated)
- Custom business metrics:
    hallucin8_embedding_cost_usd_total   Counter  — cumulative embedding spend
    hallucin8_daily_spend_usd            Gauge    — today's total spend (polled)
    hallucin8_kafka_consumer_lag         Gauge    — per-topic consumer lag
    hallucin8_circuit_breaker_state      Gauge    — 0=CLOSED 1=HALF_OPEN 2=OPEN

Endpoint: GET /metrics  (added by instrumentator.expose())
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom metric objects (module-level so they persist across requests)
# ---------------------------------------------------------------------------

try:
    from prometheus_client import Counter, Gauge

    embedding_cost_counter = Counter(
        "hallucin8_embedding_cost_usd_total",
        "Cumulative embedding API spend in USD",
        ["org_id", "job_type"],
    )

    daily_spend_gauge = Gauge(
        "hallucin8_daily_spend_usd",
        "Today's total embedding spend in USD (approximate)",
        ["org_id"],
    )

    kafka_lag_gauge = Gauge(
        "hallucin8_kafka_consumer_lag",
        "Kafka consumer group lag per topic",
        ["consumer_group", "topic"],
    )

    circuit_breaker_gauge = Gauge(
        "hallucin8_circuit_breaker_state",
        "Circuit breaker state: 0=CLOSED 1=HALF_OPEN 2=OPEN",
        ["name"],
    )

    _METRICS_AVAILABLE = True
except ImportError:
    _METRICS_AVAILABLE = False
    logger.warning("prometheus_client not installed — custom metrics unavailable")


# ---------------------------------------------------------------------------
# Instrumentation setup — call once in lifespan
# ---------------------------------------------------------------------------

def setup_metrics(app: "FastAPI") -> None:
    """Attach prometheus-fastapi-instrumentator and expose /metrics endpoint."""
    if not _METRICS_AVAILABLE:
        logger.warning("Prometheus metrics skipped — prometheus_client not installed")
        return

    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=True,
            should_instrument_requests_inprogress=True,
            excluded_handlers=["/health", "/metrics"],
            inprogress_labels=True,
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

        logger.info("Prometheus metrics endpoint registered at /metrics")
    except Exception:
        logger.exception("Failed to set up Prometheus metrics")


# ---------------------------------------------------------------------------
# Helper functions — called by services to record business events
# ---------------------------------------------------------------------------

def record_embedding_cost(org_id: str, job_type: str, cost_usd: float) -> None:
    """Increment the embedding cost counter. Call after a successful API batch."""
    if not _METRICS_AVAILABLE:
        return
    try:
        embedding_cost_counter.labels(org_id=org_id, job_type=job_type).inc(cost_usd)
    except Exception:
        pass


def set_daily_spend(org_id: str, total_usd: float) -> None:
    """Update the daily spend gauge. Called by the CostGuard or a background task."""
    if not _METRICS_AVAILABLE:
        return
    try:
        daily_spend_gauge.labels(org_id=org_id).set(total_usd)
    except Exception:
        pass


def set_kafka_lag(consumer_group: str, topic: str, lag: int) -> None:
    """Update Kafka consumer lag gauge. Called by monitoring task / consumer."""
    if not _METRICS_AVAILABLE:
        return
    try:
        kafka_lag_gauge.labels(consumer_group=consumer_group, topic=topic).set(lag)
    except Exception:
        pass


def set_circuit_breaker_state(name: str, state: str) -> None:
    """Update circuit breaker state gauge (CLOSED=0, HALF_OPEN=1, OPEN=2)."""
    if not _METRICS_AVAILABLE:
        return
    _STATE_MAP = {"CLOSED": 0, "HALF_OPEN": 1, "OPEN": 2}
    try:
        circuit_breaker_gauge.labels(name=name).set(_STATE_MAP.get(state, 0))
    except Exception:
        pass
