# PLAN.md — SGE Semantic Dominance & Brand Hallucination Monitor

> Sprint-based build roadmap for `hallucin8`.
> Each sprint = 2 weeks. Update status inline as work progresses.
> Status: `[ ]` = todo · `[~]` = in progress · `[x]` = done · `[!]` = blocked

---

## 🗺️ Milestone Overview

```
Sprint 1  ──► Foundation & Local Dev Environment
Sprint 2  ──► Kafka Ingestion Pipeline
Sprint 3  ──► Vector ETL with Airflow
Sprint 4  ──► Knowledge Graph (Neo4j) Core
Sprint 5  ──► Hallucination Detection Engine
Sprint 6  ──► API Layer & Multi-Tenant Auth
Sprint 7  ──► Dashboard MVP (Vector Map + Scores)
Sprint 8  ──► Brand Safety Reports & Alerts
Sprint 9  ──► Performance, Cost Optimization & Hardening
Sprint 10 ──► Beta Launch & Feedback Loop
```

---

## Sprint 1 — Foundation & Local Dev Environment
**Duration:** Weeks 1–2
**Goal:** Every engineer can clone the repo and run the full stack in under 10 minutes.

### Deliverables

#### Infrastructure Bootstrap
- [x] Initialize monorepo with `pnpm workspaces` + Python `pyproject.toml`
- [x] `docker-compose.yml` with all services:
  - Redpanda (Kafka-compatible, dev simplicity) + Redpanda Console
  - Neo4j 5.x
  - Qdrant
  - Redis 7
  - PostgreSQL 16
  - Airflow (LocalExecutor, behind `--profile airflow`)
- [x] `.env.example` with all required keys documented
- [x] `Makefile` with `make up`, `make down`, `make seed`, `make test` commands
- [x] Health check script: `scripts/healthcheck.sh` — validates all services are live

#### Backend Skeleton
- [x] FastAPI app with `lifespan` context manager
- [x] Alembic migration: initial schema (brands, competitors, scan_jobs, embedding_results, alerts, intent_clusters)
- [x] Pydantic v2 models for: `Brand`, `Competitor`, `ScanJob`, `EmbeddingResult`
- [x] Structlog configuration (JSON output, request ID middleware)
- [x] Pytest setup with `conftest.py`, async test client, smoke tests

#### Frontend Skeleton
- [x] Next.js 14 App Router scaffold
- [x] Tailwind config wired to brand tokens from `BRAND.md`
- [x] `@/lib/brand-tokens.ts` — exports all design tokens
- [x] Layout: `(auth)` and `(dashboard)` route groups
- [x] Placeholder pages: `/login`, `/dashboard`, `/brands/[id]`

#### BRAND.md
- [x] `BRAND.md` already provided — wired into `brand-tokens.ts` and Tailwind config

#### CI/CD
- [x] GitHub Actions: lint + test on every PR (`.github/workflows/ci.yml`)
- [x] Pre-commit hooks: ruff, mypy, detect-secrets (`.pre-commit-config.yaml`)
- [ ] Branch protection: require 1 review + passing CI — configure in GitHub repo settings

### Definition of Done
> Full `docker-compose up` runs without errors. `make test` passes. Dashboard renders
> at `localhost:3000` with correct brand colors from BRAND.md tokens.

---

## Sprint 2 — Kafka Ingestion Pipeline
**Duration:** Weeks 3–4
**Goal:** Real-time stream of brand mentions flowing into the system from 3+ sources.

### Deliverables

#### Kafka Infrastructure
- [x] Define Avro schemas for `BrandMentionEvent`, `CompetitorMentionEvent`, `ReviewEvent`
- [x] Schema Registry setup (Redpanda built-in SR on port 8081, Confluent compatible)
- [x] Topic provisioning: `infra/kafka/create_topics.sh` + `make kafka-topics`
  - `brand.mentions.raw`, `brand.mentions.enriched` (intermediate), `competitor.mentions.raw`
  - `embeddings.pending`, `hallucination.alerts`, `mentions.dlq`
- [x] Schema registration: `infra/kafka/register_schemas.sh` + `make kafka-schemas`

#### Producers (Data Sources)
- [x] **News/RSS Producer** — `feedparser`-based; brand-name keyword filter per entry
- [x] **Reddit Producer** — PRAW OAuth2 or public JSON API fallback; configurable subreddits
- [x] **Review Scraper Producer** — public RSS feeds (Trustpilot, G2); no ToS violation
- [x] **Manual Injection API** — `POST /api/v1/mentions`; 202 Accepted; Kafka publish via executor

#### Consumers
- [x] **Deduplication Consumer** — Redis SETEX on SHA-256 content_hash (30-day TTL); fail-open on Redis failure
- [x] **Enrichment Consumer** — brand lookup: Redis cache → PostgreSQL; DLQ on brand_not_found
- [x] **Routing Consumer** — routes to `embeddings.pending` + keyword-based hallucination heuristic; persists to `brand_mentions` table

#### Monitoring
- [x] Kafka lag dashboard (Grafana + Prometheus, `--profile monitoring`; `infra/monitoring/`)
- [x] Dead Letter Queue (`mentions.dlq`) for failed/unresolvable events
- [x] Prometheus alert rule: lag > 1000 messages + DLQ non-empty (`infra/monitoring/alerts/kafka_lag.yml`)

### Definition of Done
> 100+ test brand mentions flow end-to-end from producer → Kafka → consumer in an
> integration test. Zero data loss at 500 events/minute load test.

---

## Sprint 3 — Vector ETL with Airflow
**Duration:** Weeks 5–6
**Goal:** Kafka events become embeddings stored in Qdrant with cosine similarity scores calculated.

### Deliverables

#### Airflow DAGs
- [x] **`dag_embedding_batch`** — Triggered hourly; processes `embeddings.pending` queue
  - Task 1: `fetch_pending_events` — reads from PostgreSQL (embedding_queued=false)
  - Task 2: `generate_embeddings` — calls OpenAI `text-embedding-3-small` in batches of 100
  - Task 3: `calculate_cosine_distances` — vs. intent cluster centroids from Qdrant
  - Task 4: `store_vectors` — upsert to Qdrant brand_embeddings
  - Task 5: `update_sps_scores` — insert rows to sps_scores table
  - Task 6: `mark_processed` — set embedding_queued=true, clean Redis temp keys

- [x] **`dag_competitor_benchmark`** — Runs daily; generates competitor embedding snapshots
- [x] **`dag_intent_cluster_refresh`** — Weekly; refreshes intent cluster centroid vectors

#### Embedding Service
- [x] `ml/embeddings/service.py` — sync batch embedding with Redis token bucket
- [x] Embedding cache in Redis (TTL 24h) — avoid re-embedding identical text
- [x] Cost tracking: log tokens consumed per job to PostgreSQL `embedding_costs` table
- [x] Rate limit handling: respect OpenAI 1M token/min limit with token bucket (Redis sliding window)

#### Qdrant Collections
- [x] Collection: `brand_embeddings` (1536 dims, cosine distance)
- [x] Collection: `concept_embeddings` — pre-computed intent cluster vectors
- [x] Collection: `competitor_embeddings`
- [x] Payload filters on `brand_id`, `source_type`, `content_hash`, `created_at`

#### Cosine Distance Scoring
- [x] `ml/scoring/proximity.py` — `calculate_sps(brand_vector, concept_vector) -> float`
- [x] Batch score update: all active brands vs. all intent clusters
- [x] Historical SPS time-series stored in PostgreSQL (`sps_scores` table, migration 004)

### Definition of Done
> DAG runs end-to-end in < 5 min for 1000 events. SPS scores visible in DB.
> Embedding costs logged. Zero duplicate vectors in Qdrant.
> ✅ Integration test verifies all DoD conditions in-process.

---

## Sprint 4 — Knowledge Graph (Neo4j) Core
**Duration:** Weeks 7–8
**Goal:** Semantic relationships between brands, concepts, and attributes queryable via Cypher.

### Deliverables

#### Graph Schema
- [x] Full node/relationship schema in `infra/neo4j/schema.cypher`
- [x] Nodes: `Brand`, `Concept`, `Attribute`, `IntentCluster`, `Competitor`, `Source`
- [x] Relationships:
  - `(Brand)-[:ASSOCIATED_WITH {score, timestamp, source}]->(Concept)`
  - `(Brand)-[:COMPETES_WITH {market_segment}]->(Brand)`
  - `(Brand)-[:HALLUCINATED_AS {model, confidence, detected_at}]->(Attribute)`
  - `(Concept)-[:BELONGS_TO_CLUSTER]->(IntentCluster)`
  - `(Attribute)-[:CONTRADICTS]->(Attribute)`

#### Graph Population
- [x] `infra/neo4j/seed.cypher` — 6 clusters, 24 concepts, 6 attributes, 3 test brands
- [x] Airflow task `write_associations_to_graph` added to `dag_embedding_batch` (Task 7, fail-open)
- [x] Constraints + indexes in `schema.cypher` (brand_id_unique, concept_slug_unique, etc.)

#### Graph Query Layer
- [x] `apps/api/graph/queries.py` — all 4 typed query functions + `write_associations_batch`
- [x] `apps/api/graph/client.py` — `Neo4jClient` + `get_neo4j_client()` FastAPI dependency
- [x] `apps/api/routers/graph.py` — 4 REST endpoints wired to query layer
  - `GET /api/v1/brands/{brand_id}/concept-associations`
  - `GET /api/v1/brands/{brand_id}/competitor-proximity`
  - `GET /api/v1/brands/{brand_id}/hallucination-history`
  - `GET /api/v1/brands/{brand_id}/cluster-ranking`

#### Graph Admin
- [x] Neo4j Browser at `localhost:7474` (already in docker-compose, no change needed)
- [x] Cypher query safety enforced via test suite (no string interpolation assertions)

### Definition of Done
> Can execute all 4 query types via API. Neo4j Browser shows populated graph
> with 3 test brands, 20 concepts, and relationship weights.
> ✅ All 4 endpoints wired + tested. Seed script verified idempotent.

---

## Sprint 5 — Hallucination Detection Engine ✅
**Duration:** Weeks 9–10
**Goal:** Automatically detect when AI models are saying incorrect things about monitored brands.

### Deliverables

#### LLM Probing Pipeline
- [x] `ml/hallucination/prober.py` — sends structured probe queries to:
  - OpenAI GPT-4o
  - Google Gemini 1.5 Pro
  - Perplexity Sonar (future)
- [x] Probe query templates (configurable per brand):
  - "What are the main features of [Brand]?"
  - "Is [Brand] recommended for [use_case]?"
  - "Compare [Brand] with [Competitor]."
  - "What do users complain about regarding [Brand]?"

#### Ground Truth Manifest
- [x] `data/schemas/brand_manifest.py` — `BrandManifest` Pydantic model:
  - `true_attributes: list[str]`
  - `false_attributes: list[str]`
  - `competitor_list: list[str]`
  - `regulatory_claims_to_avoid: list[str]`
- [x] Admin API: `PUT /api/v1/brands/{id}/manifest` to update ground truth
- [x] `GET /api/v1/brands/{id}` — read brand with manifest
- [x] `apps/api/routers/brands.py` — wired into FastAPI app

#### Hallucination Classifier
- [x] `ml/hallucination/classifier.py`:
  - Embeds LLM response + each manifest attribute
  - Flags attribute if cosine similarity to a `false_attribute` > threshold (0.82)
  - Flags competitor confusion if competitor name appears in positive context (VADER)
  - Flags sentiment drift via VADER compound < -0.05
  - Flags regulatory claims via verbatim keyword match (always CRITICAL)
- [x] Severity scoring: `LOW | MEDIUM | HIGH | CRITICAL`
- [x] Write detected hallucinations to Neo4j `HALLUCINATED_AS` relationships
  - `write_hallucination_to_graph()` in `apps/api/graph/queries.py`
- [x] Publish `CRITICAL` hallucinations to `hallucination.alerts` Kafka topic
- [x] `apps/api/models/probe_result.py` + migration `005_add_probe_results.py`

#### Scheduled Probing
- [x] Airflow DAG: `dag_llm_probing` — runs daily 04:00 UTC per active brand (5 tasks)
- [x] Cost cap: `MAX_DAILY_PROBE_COST_USD` env var (default $2.00/day)
- [x] Configurable: model selection, competitor name, use_case per brand

#### Tests
- [x] `tests/unit/test_hallucination_classifier.py` — 28 unit tests across all 4 detectors
- [x] `tests/unit/test_prober.py` — 18 unit tests (mocked API calls, cost logic)
- [x] `tests/integration/test_hallucination_pipeline.py` — end-to-end fixture → classify
- [x] `data/fixtures/hallucination_test_cases.json` — 4 ground-truth cases (3 TP + 1 clean)

### Definition of Done
> Given a brand with a known hallucination (seeded in fixtures), the classifier
> detects it with precision > 0.85. Alert fires to Kafka. Neo4j node created.
> ✅ Integration test verifies precision gate. All 3 TP fixtures detected. Clean fixture = 0 FP.

---

## Sprint 6 — API Layer & Multi-Tenant Auth ✅
**Duration:** Weeks 11–12
**Goal:** Secure, versioned REST API. Each customer's data is fully isolated.

### Deliverables

#### Authentication & Authorization
- [x] JWT validation — HS256 (Supabase-compatible; supports both flat and app_metadata payloads)
  - `apps/api/auth/jwt.py` — `decode_jwt()`, `create_token()` (dev/test helper)
- [x] Application-level RLS — every query filtered by `organization_id` from OrgContext
  - Note: PostgreSQL-level RLS (session SET) is recommended for production (ADR pending)
- [x] `apps/api/auth/context.py` — `get_org_context()` dependency: JWT → Bearer, X-API-Key header
- [x] Roles: `admin`, `analyst`, `viewer` — enforced via `require_role()` factory in `api_keys.py`
- [x] API key support — `apps/api/auth/api_keys.py`; keys stored as SHA-256 hash
- [x] `POST /api/v1/auth/api-keys` — create key (admin only); raw key returned once
- [x] `GET /api/v1/auth/api-keys` — list keys (no raw key)
- [x] `DELETE /api/v1/auth/api-keys/{id}` — revoke (admin only)

#### Core API Endpoints
- [x] **Brands** (`apps/api/routers/brands.py`)
  - `GET /api/v1/brands` — list org's brands
  - `POST /api/v1/brands` — create brand with manifest
  - `GET /api/v1/brands/{id}` — get single brand
  - `PUT /api/v1/brands/{id}/manifest` — update ground truth manifest
  - `GET /api/v1/brands/{id}/sps` — time-series SPS scores
  - `GET /api/v1/brands/{id}/hallucinations` — probe result history

- [x] **Competitors** (`apps/api/routers/competitors.py`)
  - `GET /api/v1/brands/{id}/competitors` — list tracked competitors
  - `POST /api/v1/brands/{id}/competitors` — add competitor to monitor
  - `DELETE /api/v1/brands/{id}/competitors/{cid}` — remove competitor

- [x] **Vector Map** (`apps/api/routers/vector_map.py`)
  - `GET /api/v1/brands/{id}/vector-map` — 2D SPS position snapshot
  - `GET /api/v1/brands/{id}/vector-map/stream` — SSE live updates (30s)

- [x] **Alerts** (`apps/api/routers/alerts.py`)
  - `GET /api/v1/alerts` — paginated alert history (severity + acknowledged filters)
  - `PATCH /api/v1/alerts/{id}/acknowledge` — mark acknowledged
  - `POST /api/v1/alerts/webhooks` — register delivery endpoint
  - `GET /api/v1/alerts/webhooks` — list webhook endpoints

- [x] **Scan Jobs** (`apps/api/routers/scan_jobs.py`)
  - `POST /api/v1/scan-jobs` — trigger on-demand scan (202 Accepted, Celery)
  - `GET /api/v1/scan-jobs/{id}` — job status + result

#### API Quality
- [x] OpenAPI spec auto-generated at `/api/docs` (FastAPI default)
- [x] Rate limiting: 100 req/min per org (Redis sliding window in `get_org_context`)
- [x] Request ID propagation — already in `RequestIDMiddleware` (Sprint 1)
- [x] Error envelope: `{ error: { code, message, details } }` — `middleware/error_handler.py`
- [x] Migration `006_add_auth_tables.py` — `api_keys` + `webhook_endpoints` tables

#### Tests
- [x] `tests/unit/test_auth_jwt.py` — JWT creation, decode, Supabase format, expiry
- [x] `tests/unit/test_auth_api_keys.py` — key generation, hashing, require_role guard
- [x] `tests/integration/test_multi_tenant_isolation.py` — Org A ≠ Org B across brands/alerts/competitors

### Definition of Done
> Postman collection covers all endpoints. Multi-tenant isolation verified via
> integration tests (Org A cannot read Org B's data). OpenAPI spec exported.
> ✅ Integration tests confirm 404 for cross-org reads. Error envelope verified on all error types.

---

## Sprint 7 — Dashboard MVP (Vector Map + Scores)
**Duration:** Weeks 13–14
**Goal:** CMO-facing dashboard showing semantic position, hallucination alerts, competitor map.

> ⚠️ ALL component styling MUST reference BRAND.md before implementation.

### Deliverables

#### Core Dashboard Pages
- [ ] **`/dashboard`** — Overview: SPS score cards, alert count, last scan timestamp
- [ ] **`/brands/[id]`** — Brand detail with tabs:
  - Overview (SPS trend chart)
  - Vector Map
  - Hallucinations
  - Competitors

#### Vector Scatter Plot (Key Feature)
- [ ] Interactive 2D scatter plot (Recharts + D3 zoom/pan)
- [ ] Each point = a brand or concept, colored by intent cluster (colors from BRAND.md viz palette)
- [ ] Hover tooltip: brand name, SPS score, closest cluster label
- [ ] Filter panel: show/hide clusters, competitors, time range
- [ ] Animate point movement when new scores load
- [ ] Legend follows BRAND.md data visualization spec

#### SPS Score Trend Chart
- [ ] Line chart: SPS per intent cluster over time
- [ ] Benchmark line: industry average (anonymized)
- [ ] Annotations: mark dates when hallucinations were detected

#### Hallucination Feed
- [ ] Card list: severity badge (color from BRAND.md), model name, detected attribute, timestamp
- [ ] "View Response" expandable — shows full LLM response that triggered flag
- [ ] Acknowledge + resolve workflow
- [ ] Filter by severity, model, date range

#### Auth UI
- [ ] Login page (email + magic link)
- [ ] Org setup onboarding (brand name, competitors, manifest upload)

### Definition of Done
> Design-reviewed against BRAND.md. Vector map renders 50 points at 60fps.
> Hallucination feed shows live data. Lighthouse score > 85.

---

## Sprint 8 — Brand Safety Reports & Alerts
**Duration:** Weeks 15–16
**Goal:** Automated reporting and alerting so customers get value without checking the dashboard.

### Deliverables

#### Automated Reports
- [x] Weekly PDF report generator (ReportLab):
  - Executive summary: SPS delta vs. last week
  - Top 5 hallucinations detected
  - Competitor movement in vector space
  - Recommended actions (template-based, configurable)
- [x] Email delivery via Resend API
- [x] Report archive: `GET /api/v1/reports` — list + download

#### Alerting System
- [x] **Slack Integration** — Block Kit JSON, CRITICAL/HIGH only
- [x] **Email Alerts** — instant CRITICAL via Resend; daily digest via Airflow DAG
- [x] **Webhook** — generic JSON payload with HMAC-SHA256 signature
- [x] Alert rules engine: customers define custom thresholds
  - "Alert if SPS for 'reliability' drops below 0.6"
  - "Alert if competitor X enters top 3 in any intent cluster"

#### Compliance Export
- [x] `GET /api/v1/brands/{id}/compliance-export` — JSONL export of:
  - All hallucinations (model, prompt, response, severity, timestamp)
  - SPS score history
  - Ground truth manifest versions
- [x] Used for regulatory/legal evidence that a model was making false claims

### Definition of Done
> Weekly report emails land in inbox with correct data. Slack alert fires within
> 60s of a CRITICAL hallucination being detected. Compliance export passes schema validation.

---

## Sprint 9 — Performance, Cost Optimization & Hardening
**Duration:** Weeks 17–18
**Goal:** System is production-grade: cheap to run, hard to break, easy to monitor.

### Deliverables

#### Cost Optimization
- [x] Embedding deduplication: skip re-embedding text with same SHA-256 hash (Redis cache, already in Sprint 3)
- [x] Tiered probing: probe GPT-4o-mini daily, Gemini weekly (configurable via settings)
- [x] Qdrant quantization: `scripts/init_qdrant_quantization.py` — scalar int8, 4x storage reduction
- [x] Airflow task-level cost tagging: `infra_costs` table + `dag_backup.py` records metadata
- [x] Cost dashboard widget: `GET /api/v1/costs/{summary,breakdown,infra}` + `/costs` page
- [x] Hard budget cap: `CostGuard.check_budget()` raises `BudgetExceededError` before API calls

#### Performance
- [x] Vector map API: < 200ms P95 — Redis cache (1h TTL) in `vector_map.py`
- [x] Dashboard initial load: RSC layout + TanStack Query caching
- [x] Kafka consumer throughput benchmark: k6 load test (`tests/k6/load_test.js`)
- [ ] Neo4j query tuning: EXPLAIN all queries, add missing indexes (deferred — Sprint 10)
- [x] Load test: k6 script for 100 concurrent users, P95 < 200ms SLA threshold

#### Reliability & Hardening
- [x] Circuit breakers: `CircuitBreaker` (tenacity + Redis) on OpenAI, Slack, Resend, webhooks
- [x] Graceful degradation: Qdrant unavailable → Redis-cached vector map served (see runbook)
- [x] Idempotent Kafka consumers: Redis `routed:{hash}` guard in `RoutingConsumer`
- [x] Database connection pooling: PgBouncer `--profile pgbouncer` + asyncpg `statement_cache_size=0`
- [x] Automated daily backups: `dag_backup.py` — pg_dump + Neo4j export → GCS (02:00 UTC)

#### Observability
- [x] Grafana dashboards: kafka_lag.json, embedding_costs.json, airflow_dag_health.json
- [x] Sentry integration: backend (`sentry-sdk[fastapi]`) + frontend (`@sentry/nextjs`)
- [ ] Uptime monitoring: Better Uptime / external synthetic checks (deferred — Sprint 10)
- [x] On-call runbook: `docs/runbooks/` (on_call.md + 3 incident runbooks)

### Definition of Done
> Load test passes. P95 API latency < 200ms. Embedding cost < $0.10/brand/day at
> 1000 mentions/day volume. Zero data loss in Kafka consumer replay test.

---

## Sprint 10 — Beta Launch & Feedback Loop
**Duration:** Weeks 19–20
**Goal:** 5 paying beta customers onboarded. Feedback loop instrumented.
**Status: Complete (2026-05-15)**

### Deliverables

#### Onboarding
- [x] Self-serve signup flow: email → org creation → brand setup wizard → first scan
- [x] Interactive product tour (Shepherd.js — styled per BRAND.md)
- [x] Sample data mode: pre-populated fictional brand for demo/evaluation (`POST /api/v1/onboarding/demo/seed`)
- [x] Onboarding email sequence (D+0, D+3, D+7) via Resend + Airflow DAG

#### Customer Success Tooling
- [x] Internal admin panel (`/admin`): org list, scan job management, cost per org, NPS responses
- [x] Support ticket integration (Intercom widget — positioned per BRAND.md, above NPS survey)
- [x] Usage analytics: PostHog events for key actions (scan triggered, report downloaded, alert acknowledged, tour completed, NPS submitted)

#### Feedback Instrumentation
- [x] In-app NPS survey modal (triggered after first report; stores to `nps_responses` table)
- [x] Feature flag system (homegrown — Redis-cached, DB-backed, org-level overrides)
- [x] Error boundary with "Report Issue" button → creates GitHub issue via API
- [x] Changelog page `/changelog` — Fraunces + Plus Jakarta Sans per BRAND.md

#### Launch Checklist
- [x] SOC 2 readiness checklist reviewed — gap analysis in `docs/security/soc2_gap_analysis.md`
- [x] Privacy policy + Terms of Service pages live (`/privacy`, `/terms`)
- [x] GDPR: data deletion endpoint `DELETE /api/v1/organizations/{id}` (cascades all data + Qdrant/Neo4j best-effort)
- [x] SSL, HSTS, security headers — full CSP, X-Frame-Options, Permissions-Policy, HSTS (prod), SecurityHeadersMiddleware (FastAPI)
- [x] Penetration test scope defined — `docs/security/pentest_scope.md` (test scheduled pre-GA Q3 2026)

### Definition of Done
> 5 beta customers have completed full onboarding without engineering support.
> NPS > 30. No P0/P1 bugs open. PostHog tracking key funnels.

---

## 📊 Capacity & Resourcing Assumptions

| Role | Sprints Involved | Notes |
|---|---|---|
| Backend Engineer (x2) | S1–S10 | Python, FastAPI, Kafka, Airflow |
| ML Engineer (x1) | S3–S5, S9 | Embeddings, clustering, hallucination detection |
| Frontend Engineer (x1) | S1, S6–S8 | Next.js, D3, Recharts |
| DevOps / Platform (x1) | S1, S9–S10 | Docker, GCP, Grafana |
| Product / Design (x1) | S1 (BRAND.md), S7, S10 | Design system, UX review |

---

## 🚨 Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OpenAI API cost overrun | HIGH | HIGH | Aggressive caching, tiered probing, hard spend caps (Sprint 9) |
| LLM output non-determinism breaks hallucination detection | MEDIUM | HIGH | Threshold tuning, human-review queue for borderline cases |
| Competitor data scraping ToS violation | MEDIUM | HIGH | Use only public RSS/APIs; legal review before scraping |
| Neo4j query performance at scale | MEDIUM | MEDIUM | Index tuning in Sprint 9; Qdrant fallback for pure vector queries |
| "Manipulation" framing backlash | LOW | HIGH | Always position as "Brand Safety & AI Compliance" — see CLAUDE.md Hard Rules |

---

## 🔁 Backlog (Post-Sprint 10)

- 3D vector space visualization (Three.js)
- Multi-model comparison dashboard (GPT vs Gemini vs Llama side-by-side)
- White-label report exports (customer logo — tokens from BRAND.md)
- API for content teams: "What should I publish to improve SPS for 'reliability'?"
- Webhook → Zapier certified integration
- SOC 2 Type II audit
- Enterprise SSO (SAML/OIDC)
- Public benchmark index: "AI Brand Visibility Index" (anonymized, top 500 SaaS brands)
