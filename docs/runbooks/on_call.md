# On-Call Runbook — hallucin8

> Last updated: 2026-05-14
> On-call rotation: #hallucin8-oncall Slack channel

---

## Quick reference

| Symptom | Runbook |
|---|---|
| Kafka consumer lag > 10 000 | [kafka_consumer_lag.md](kafka_consumer_lag.md) |
| Daily embedding spend near cap | [high_embedding_cost.md](high_embedding_cost.md) |
| Qdrant API returning 5xx | [qdrant_unavailable.md](qdrant_unavailable.md) |
| API P95 > 200ms | [api_latency.md](#api-latency-degradation) |
| Airflow DAG failing | Grafana → Airflow DAG Health dashboard |
| Circuit breaker OPEN | Check Grafana → Embedding Costs → "Circuit Breaker States" |

---

## Contacts

| Role | Contact |
|---|---|
| Primary on-call | @hallucin8-oncall (Slack) |
| Infra | @infra-team |
| Data/ML | @ml-team |
| Escalation | PagerDuty: hallucin8-api service |

---

## Service URLs (internal)

| Service | URL |
|---|---|
| API | http://api.hallucin8.internal:8000 |
| Grafana | http://monitoring.hallucin8.internal:3001 |
| Prometheus | http://monitoring.hallucin8.internal:9090 |
| Redpanda Console | http://monitoring.hallucin8.internal:8080 |
| Airflow | http://airflow.hallucin8.internal:8085 |

---

## Severity definitions

| Level | Definition | Response SLA |
|---|---|---|
| P1 | Customer-facing outage; data loss | 15 minutes |
| P2 | Degraded performance or missed SLA | 1 hour |
| P3 | Non-critical feature broken | Next business day |

---

## General triage steps

1. Check Grafana → **Embedding Costs & Budget** for API error rates and latency.
2. Check Grafana → **Kafka / Redpanda Lag** for consumer backlog.
3. Check Airflow → **DAGs** view for failed runs.
4. Check Sentry for recent unhandled exceptions.
5. Check `docker-compose ps` on the host for container health.

```bash
# Common diagnostics
docker-compose ps
docker-compose logs --tail=50 api
docker-compose logs --tail=50 redis
curl -sf http://localhost:8000/health
curl -sf http://localhost:6333/healthz    # Qdrant
redis-cli -h localhost ping
```

---

## API latency degradation

**Symptoms:** Grafana P95 > 200ms; users report slow dashboard.

**Investigation:**
1. Check Redis: `redis-cli INFO stats | grep keyspace_hits` — if hit rate drops, cache is cold.
2. Check DB pool: look for `QueuePool limit exceeded` in API logs.
3. Check Qdrant: `curl http://localhost:6333/telemetry` — response time field.

**Remediation:**
- Redis cold cache: wait ~1h for vector map cache to warm up; or pre-warm with:
  ```bash
  python scripts/warm_vector_map_cache.py
  ```
- DB pool exhausted: restart the API process; consider increasing `pool_size` in `database.py`.
- Qdrant slow: see [qdrant_unavailable.md](qdrant_unavailable.md).

---

## Deployment checklist

Before deploying to production:
1. `pytest tests/ -v` — all tests pass
2. `alembic upgrade head` — migrations applied
3. `python scripts/init_qdrant_quantization.py --dry-run` — quantization config verified
4. `k6 run tests/k6/load_test.js` — P95 < 200ms confirmed
5. Sentry release tagged: `sentry-cli releases new <version>`
