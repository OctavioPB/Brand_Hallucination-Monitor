# Runbook: Qdrant Unavailable / Graceful Degradation

**Alert trigger:** Qdrant health check fails; vector map API returns 500s

---

## Graceful degradation behaviour

When Qdrant is unavailable, hallucin8 degrades gracefully:

| Feature | Degraded behaviour |
|---|---|
| Vector map | Served from Redis cache (1h TTL) — stale but not broken |
| SPS scores | Read from PostgreSQL `sps_scores` table — always available |
| New embeddings | Queued in Celery / Redis — processed when Qdrant recovers |
| Brand hallucination probing | Unaffected (uses OpenAI / Gemini directly) |

The circuit breaker (`hallucin8_circuit_breaker_state{name="qdrant"}`) opens
after 5 consecutive failures, preventing cascade timeouts.

---

## Investigation

```bash
# 1. Check Qdrant container
docker-compose ps qdrant
docker-compose logs --tail=50 qdrant

# 2. Direct health check
curl -sf http://localhost:6333/healthz && echo "OK" || echo "FAILED"

# 3. Check disk space (Qdrant fails if storage is full)
df -h /var/lib/docker/volumes/hallucin8_qdrant_data

# 4. Check collection status
curl http://localhost:6333/collections | python3 -m json.tool
```

---

## Remediation

### Container OOM / crash
```bash
docker-compose restart qdrant
# Wait 30s for healthcheck to pass
docker-compose logs -f qdrant
```

### Disk full
```bash
# Check storage
du -sh /var/lib/docker/volumes/hallucin8_qdrant_data

# Option 1: Delete old snapshots
ls /var/lib/docker/volumes/hallucin8_qdrant_data/_data/snapshots/
# Remove snapshots > 7 days old

# Option 2: Trigger Qdrant optimizer to compact segments
curl -X POST http://localhost:6333/collections/brands_reliability/index
```

### Corrupted collection
```bash
# List collections
curl http://localhost:6333/collections

# Restore from backup (if GCS backup available)
gsutil cp gs://${GCS_BACKUP_BUCKET}/hallucin8/backups/qdrant/latest/ /tmp/qdrant-restore/
# Then restore via Qdrant snapshot API

# If no backup: re-run the Airflow ETL DAG to rebuild vectors from PostgreSQL
airflow dags trigger dag_vector_etl
```

---

## Verifying recovery

```bash
# Confirm Qdrant is healthy
curl -sf http://localhost:6333/healthz

# Check circuit breaker state (should return to CLOSED)
curl http://localhost:8000/api/v1/status | python3 -m json.tool

# Verify vector map is served live (not from cache)
# Delete cache key and confirm fresh response
redis-cli DEL "vmap:v1:org_alpha:<brand_id>"
curl http://localhost:8000/api/v1/brands/<brand_id>/vector-map
```

---

## Prevention

- Enable scalar quantization to reduce Qdrant storage 4x:
  ```bash
  python scripts/init_qdrant_quantization.py
  ```
- Monitor `df -h` in Grafana node-exporter (add disk panel to Airflow DAG Health dashboard)
- Set Qdrant `storage.optimizers.max_segment_size_kb` to limit segment growth
