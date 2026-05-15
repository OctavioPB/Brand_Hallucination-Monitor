# Runbook: High Embedding Cost / Budget Exceeded

**Alert trigger:** `hallucin8_daily_spend_usd > MAX_DAILY_SPEND_USD * 0.9`
**Hard cap:** `CostGuard.check_budget()` raises `BudgetExceededError` at 100%

---

## Background

The daily embedding budget is set via `MAX_DAILY_SPEND_USD` (default: $5.00).
When exceeded, `EmbeddingService.embed_batch()` raises `BudgetExceededError`
and new embedding jobs are blocked until the next UTC day.

Spend is tracked in `embedding_costs` table. Cache hits (Redis) cost $0.

---

## Investigation

```bash
# 1. Check today's spend in the Costs dashboard
open http://localhost:3000/costs

# 2. Query the DB directly
psql -U hallucin8 -d hallucin8 -c "
SELECT
  DATE(logged_at) AS day,
  job_type,
  SUM(cost_usd)::numeric(12,4) AS cost,
  COUNT(*) AS calls,
  SUM(n_cached) AS cache_hits
FROM embedding_costs
WHERE DATE(logged_at) = CURRENT_DATE
GROUP BY 1, 2
ORDER BY cost DESC;
"

# 3. Check cache hit rate (low hits = many uncached texts)
redis-cli INFO stats | grep keyspace
```

---

## Immediate actions

### If budget is exceeded (embeddings blocked)
The system is in **fail-safe mode** — ingestion continues but embeddings are queued,
not processed. This is intentional; no data is lost.

```bash
# Option 1: Wait until UTC midnight (automatic reset)
# Option 2: Increase the cap temporarily (requires restart)
# In .env.local:
MAX_DAILY_SPEND_USD=10.00
docker-compose restart api worker
```

### If spend is abnormally high (cache miss storm)
A cold Redis restart or a new brand onboarding with many unique texts can spike spend.

```bash
# Check what's consuming the most tokens today
psql -U hallucin8 -d hallucin8 -c "
SELECT dag_run_id, job_type, tokens_input, cost_usd
FROM embedding_costs
WHERE DATE(logged_at) = CURRENT_DATE
ORDER BY tokens_input DESC LIMIT 10;
"

# If a specific DAG run is the culprit — terminate it
airflow dags pause <dag_id>
```

### Tiered probing cost spike
If `job_type = 'llm_probe'` is driving costs, check the probe model tier:
- Daily model: `gpt-4o-mini` (~$0.15/1M tokens)
- Weekly model: `gemini-1.5-pro` (~$0.35/1M tokens)

Misconfigured `PROBE_WEEKLY_MODEL` running daily = 2.3x expected cost.

```bash
grep PROBE_WEEKLY_MODEL .env.local
```

---

## Long-term remediation

1. Enable Qdrant quantization: `python scripts/init_qdrant_quantization.py`
   — reduces embedding storage, indirectly reduces re-embedding frequency.
2. Review `CACHE_TTL_SECONDS` in `ml/embeddings/service.py` (default 24h).
   Increasing to 72h reduces re-embedding for stable content.
3. Add deduplication at the Kafka level (dedup consumer is already there,
   but verify `content_hash` uniqueness rate in `brand_mentions`).
