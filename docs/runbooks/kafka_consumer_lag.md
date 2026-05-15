# Runbook: Kafka Consumer Lag

**Alert trigger:** `hallucin8_kafka_consumer_lag > 10000` for > 5 minutes

---

## Background

hallucin8 runs three Kafka consumer groups:

| Group | Input topic | Output |
|---|---|---|
| `hallucin8-dedup-consumer` | `brand.mentions.raw` | `brand.mentions.enriched` |
| `hallucin8-enrichment-consumer` | `brand.mentions.enriched` | `brand.mentions.enriched` (updated) |
| `hallucin8-routing-consumer` | `brand.mentions.enriched` | `embeddings.pending`, DB, `hallucination.alerts` |

Lag accumulates when consumers are slower than producers. Common causes:
- Consumer process crash or OOM
- DB write bottleneck in `RoutingConsumer._persist_mention()`
- Redis connection failure (dedup guard disabled → slower processing)
- Upstream ingestion spike (RSS feed, Reddit burst)

---

## Investigation

```bash
# 1. Check consumer process status
docker-compose ps

# 2. Tail consumer logs
docker-compose logs --tail=100 worker

# 3. Check Redpanda Console for lag per partition
open http://localhost:8080

# 4. Check current lag via rpk CLI
rpk group describe hallucin8-routing-consumer

# 5. Check Redis for idempotency set size (large = processing catch-up)
redis-cli DBSIZE
redis-cli KEYS "routed:*" | wc -l
```

---

## Remediation

### Consumer crash
```bash
docker-compose restart worker
# Monitor lag in Grafana — should start decreasing within 60s
```

### DB write bottleneck
Check if `brand_mentions` table has grown large without VACUUM:
```sql
SELECT pg_size_pretty(pg_total_relation_size('brand_mentions'));
VACUUM ANALYZE brand_mentions;
```

### Sustained high lag (> 1M messages)
1. Scale consumers horizontally (increase Celery worker count)
2. Temporarily pause ingestion sources (RSS, Reddit) to let consumers catch up:
   ```bash
   # Pause the RSS producer task
   celery -A apps.workers.celery_app control revoke <task_id> --terminate
   ```
3. If lag is in `mentions.dlq` (dead letter queue), inspect failed messages:
   ```bash
   rpk topic consume mentions.dlq --num 5
   ```

### Reset consumer offset (last resort — data loss risk)
Only if messages are unprocessable and blocking the pipeline:
```bash
# DANGER: skips unprocessed messages
rpk group seek hallucin8-routing-consumer --to end --topics brand.mentions.enriched
```

---

## Post-incident

- Document root cause in incident log
- If DLQ grew: write analysis of failed message types
- Consider adding `max.poll.interval.ms` tuning if timeouts were the cause
