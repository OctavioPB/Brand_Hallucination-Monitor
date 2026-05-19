# hallucin8

**SGE Semantic Dominance & Brand Hallucination Monitor**

> *Your brand exists in the vector space of every AI. We tell you where you are, where you need to be, and what lies the models are telling about you.*

---

## What it does

Every major AI model — ChatGPT, Gemini, Perplexity, Claude — has already formed an opinion about your brand. It is encoded in their latent space, shaped by the data they were trained on, and it influences every recommendation they give your potential customers. There is no audit trail, no baseline measurement, and no alert when it changes.

**hallucin8** gives brand and marketing teams the infrastructure to:

- **Detect hallucinations** — factual errors, competitor confusion, and regulatory misattribution in AI-generated content, flagged against your verified brand manifest
- **Measure semantic proximity** — continuous SPS scores tracking how strongly each model associates your brand with the concepts that drive purchase intent: reliability, innovation, compliance, market leadership, pricing value, support quality
- **Track competitor positioning** inside AI latent space, not just search rankings
- **Get alerted** when perception shifts, with configurable thresholds and webhook / email delivery
- **Audit AI compliance** — a timestamped, reportable record that your brand is being represented accurately across models

This is **Brand Safety & AI Compliance** infrastructure, not SEO manipulation.

---

## Architecture

```
External sources (mentions, reviews)        LLM Probe Engine (GPT-4o · Gemini · Claude)
            │                                           │
            ▼                                           ▼
     Kafka Topics ──────────────► Celery Workers ──► OpenAI Embeddings (text-embedding-3-small)
                                        │                       │
                                        │                       ▼
                                        │              Qdrant  (vector store · 1536-dim)
                                        │              Neo4j   (knowledge graph)
                                        └────────────► PostgreSQL (metadata · orgs · jobs)
                                                       Redis   (cache · queues · rate limits)
                                                            │
                                                            ▼
                                                  FastAPI REST / SSE
                                                            │
                                             ┌──────────────┼──────────────┐
                                             ▼              ▼              ▼
                                     Next.js Dashboard  Webhooks       Alert emails
```

### Core concepts

**Semantic Proximity Score (SPS)** — cosine similarity between a brand's mean embedding and a concept anchor vector in the 1536-dimensional space of `text-embedding-3-small`. Computed independently per intent cluster per LLM.

```
SPS(b, c) = cos(b, c) = (b · c) / (‖b‖ · ‖c‖)    b, c ∈ ℝ¹⁵³⁶
```

**Brand Hallucination** — when a probed LLM associates a brand with false attributes, conflates it with a competitor, or outputs a regulatory claim that must not be attributed to the brand. Detected against the brand manifest.

**Brand Manifest** — the ground truth each org defines: `true_attributes`, `false_attributes`, `competitor_list`, `regulatory_claims_to_avoid`. All hallucination detection is relative to this manifest.

**Intent Clusters** — six pre-defined semantic buckets used as scoring dimensions: `reliability · innovation · pricing_value · market_leadership · compliance · support_quality`.

---

## Tech stack

### Backend

| Layer | Technology | Notes |
|---|---|---|
| API | FastAPI 0.111 + Uvicorn | Async, OpenAPI auto-docs |
| ORM | SQLAlchemy 2 + Alembic | Migrations 001–009 |
| Task queue | Celery + Redis | Async embedding + probe jobs |
| Stream broker | Apache Kafka (Redpanda) | Brand-events topic, multi-consumer |
| Orchestration | Apache Airflow 2.9 | Vector ETL DAGs |
| Vector DB | Qdrant | Cosine search, per-brand partitions |
| Knowledge graph | Neo4j 5 | `(Brand)-[:ASSOCIATED_WITH]->(Concept)` |
| Cache | Redis 7 | Embedding cache, rate limits, Celery |
| Relational DB | PostgreSQL 16 | Orgs, brands, scores, alerts, jobs |
| Language | Python 3.12 | Strict mypy, Ruff, Pydantic v2 |

### Frontend

| Layer | Technology | Notes |
|---|---|---|
| Framework | Next.js 14 (App Router) | React Server Components |
| Charts | Recharts | SPS trend lines, cluster radar |
| Server state | TanStack Query v5 | Hooks per resource |
| Client state | Zustand | Auth context |
| Product tour | Shepherd.js | Onboarding walkthrough |
| Analytics | PostHog | Funnel + feature flags |
| Error tracking | Sentry 8 | Frontend + backend |

### ML / AI

| Model | Usage | Schedule |
|---|---|---|
| `text-embedding-3-small` | Vector generation (1536-dim) | Every scan job |
| GPT-4o | Brand perception probing | Configurable |
| Gemini 1.5 Pro | Deep brand probing | Configurable |
| Claude Opus | Probe cross-validation | Configurable |

---

## Prerequisites

- Docker Desktop 4.x (or Docker Engine + Compose v2)
- Python 3.12+
- Node.js 20+
- OpenAI API key

Optional (full feature set):
- Gemini API key — multi-model probing
- Resend API key — alert emails and onboarding sequence
- Sentry DSN — error tracking

---

## Quick start

### 1. Clone and configure

```bash
git clone https://github.com/opb-ai-lab/hallucin8.git
cd hallucin8
cp .env.example .env.local
```

Edit `.env.local` — minimum required:

```bash
OPENAI_API_KEY=sk-...
JWT_SECRET=<strong-random-string>
```

All other variables have working defaults for local development.

### 2. Install dependencies

```bash
# Python
pip install -e ".[dev]"

# Frontend
cd apps/dashboard && npm install
```

### 3. Start infrastructure

```bash
docker-compose up -d
```

Starts: PostgreSQL 16, Redis 7, Qdrant, Neo4j 5, Redpanda (Kafka).

### 4. Run migrations

```bash
cd apps/api && alembic upgrade head
```

### 5. Start the API

Run from the project root:

```bash
uvicorn apps.api.main:app --reload --port 8000
```

Swagger UI: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

### 6. Start the dashboard

```bash
cd apps/dashboard && npm run dev
```

Dashboard: [http://localhost:3000](http://localhost:3000)

The dashboard auto-seeds the AcmeCorp demo org on first visit and stores the API key in `localStorage` under `hallucin8_api_key`.

### 7. Seed demo data manually (optional)

```bash
curl -X POST http://localhost:8000/api/v1/onboarding/demo/seed
```

Creates `AcmeCorp` pre-populated with SPS scores across 6 clusters (14-day history), 4 probe results from 3 LLMs, and 3 baseline alerts.

### 8. Create your own org and trigger a scan

```bash
# Sign up — returns your API key
curl -X POST http://localhost:8000/api/v1/onboarding/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@company.com", "org_name": "My Company"}'

# Trigger a scan (replace <api-key> and <brand-id>)
curl -X POST http://localhost:8000/api/v1/scan-jobs \
  -H "X-API-Key: <api-key>" \
  -H "Content-Type: application/json" \
  -d '{"brand_id": "<brand-id>", "job_type": "llm_probe"}'
```

---

## Dashboard pages

| Route | Description |
|---|---|
| `/dashboard` | Overview — SPS trend charts, recent alerts, brand health KPIs |
| `/brands` | Brand registry — list all brands, create new brand with manifest and optional seed data |
| `/brands/[id]` | Brand detail — per-cluster SPS history, probe results, hallucination log |
| `/alerts` | Alert feed — severity filter, acknowledge, view linked probe results |
| `/info` | Product overview — Business view and Engineering view with architecture diagram |
| `/admin` | Admin overview — org KPIs, data management (clear DB / seed AcmeCorp) |
| `/admin/orgs` | All organizations — plan, brand count, scan count, spend, onboarding status |
| `/admin/scan-jobs` | All scan jobs — status filter, job type, timestamps |
| `/admin/costs` | Embedding cost breakdown by job type — 7d / 30d / 90d |
| `/admin/nps` | NPS responses — score, comment, trigger, computed NPS metric |

Admin routes are protected by `X-Admin-Secret` header (`ADMIN_SECRET` env var, default `change-me-admin-secret`).

---

## Optional profiles

### Airflow (Vector ETL orchestration)

```bash
docker-compose --profile airflow up -d
```

Airflow UI: [http://localhost:8085](http://localhost:8085) · `admin / admin`

DAGs:
- `dag_vector_etl` — daily embedding pipeline
- `dag_weekly_report` — Sunday 08:00 UTC brand safety report
- `dag_backup` — daily 02:00 UTC PostgreSQL + Neo4j → GCS
- `dag_onboarding_emails` — D+3 / D+7 email sequence

### Monitoring (Prometheus + Grafana)

```bash
docker-compose --profile monitoring up -d
```

- Prometheus: [http://localhost:9090](http://localhost:9090)
- Grafana: [http://localhost:3001](http://localhost:3001) · `admin / admin`

Pre-loaded dashboards: Kafka consumer lag, embedding costs, Airflow DAG health.

### Start everything

```bash
docker-compose --profile airflow --profile monitoring up -d
```

---

## Development commands

```bash
# Run tests
pytest tests/ -v --cov=apps/api

# Lint + format (Python)
ruff check . && ruff format .

# Type check
mypy apps/api apps/workers

# Frontend lint
cd apps/dashboard && npm run lint

# New Alembic migration
cd apps/api && alembic revision --autogenerate -m "description"

# Load test (requires k6)
k6 run tests/k6/load_test.js
```

---

## Service URLs (local dev)

| Service | URL | Credentials |
|---|---|---|
| Dashboard | http://localhost:3000 | — |
| API | http://localhost:8000 | — |
| API docs | http://localhost:8000/api/docs | — |
| Qdrant UI | http://localhost:6333/dashboard | — |
| Neo4j Browser | http://localhost:7474 | `neo4j / hallucin8pass` |
| Redpanda Console | http://localhost:8080 | — |
| Airflow | http://localhost:8085 | `admin / admin` |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3001 | `admin / admin` |

---

## Project structure

```
hallucin8/
├── apps/
│   ├── api/                       FastAPI backend (Python 3.12)
│   │   ├── models/                SQLAlchemy ORM models
│   │   │   ├── brand.py           BrandORM + BrandManifest
│   │   │   ├── onboarding.py      OrganizationORM, OnboardingStateORM, NpsResponseORM
│   │   │   ├── scan_job.py        ScanJobORM
│   │   │   ├── sps_score.py       SPSScoreORM
│   │   │   ├── probe_result.py    ProbeResultORM (hallucination records)
│   │   │   ├── db.py              AlertORM, AlertRuleORM, AlertNotificationORM
│   │   │   ├── embedding_cost.py  EmbeddingCostORM (cost tracking per dag_run)
│   │   │   ├── api_key.py         ApiKeyORM
│   │   │   └── webhook.py         WebhookEndpointORM
│   │   ├── routers/               API endpoints (/api/v1/...)
│   │   │   ├── admin.py           Internal admin panel — org list, scan jobs, costs, NPS, DB ops
│   │   │   ├── brands.py          Brand CRUD + seed endpoint
│   │   │   ├── onboarding.py      Signup, wizard steps, demo seed
│   │   │   ├── alerts.py          Alert management + acknowledgement
│   │   │   └── scan_jobs.py       Job dispatch + status polling
│   │   ├── services/              Business logic (cost guard, circuit breaker, reports)
│   │   ├── middleware/            Request ID, metrics, security headers, HSTS
│   │   ├── migrations/            Alembic migrations (001–009)
│   │   └── auth/                  API key hashing + org context extraction
│   ├── dashboard/                 Next.js 14 frontend
│   │   └── src/
│   │       ├── app/
│   │       │   ├── (dashboard)/   Authenticated dashboard routes
│   │       │   │   ├── dashboard/ Overview page
│   │       │   │   ├── brands/    Brand registry + create modal
│   │       │   │   ├── alerts/    Alert feed with severity filters
│   │       │   │   └── info/      Product overview (Business + Engineering views)
│   │       │   └── (admin)/       Admin panel routes
│   │       │       ├── admin/     Overview + data management
│   │       │       ├── admin/orgs/
│   │       │       ├── admin/scan-jobs/
│   │       │       ├── admin/costs/
│   │       │       └── admin/nps/
│   │       ├── components/        Nav, DemoInit, Eyebrow, ...
│   │       ├── hooks/             TanStack Query hooks (useBrands, useAlerts, ...)
│   │       └── lib/               brand-tokens.ts, api-client.ts, posthog, feature-flags
│   └── workers/                   Celery async workers
│       ├── consumers/             Kafka consumers (dedup, enrichment, routing)
│       └── tasks/                 Celery tasks (scan, embedding)
├── infra/
│   ├── airflow/dags/              Airflow DAG definitions
│   ├── kafka/                     Topic configs + Avro schemas
│   ├── neo4j/                     Cypher queries + schema
│   ├── monitoring/                Prometheus config + Grafana dashboards
│   └── vector-db/                 Qdrant collection configs
├── ml/
│   ├── embeddings/                Embedding service (OpenAI + circuit breaker + cost guard)
│   ├── clustering/                t-SNE / UMAP projection
│   ├── hallucination/             Hallucination detection pipeline
│   └── scoring/                   SPS computation
├── tests/
│   ├── unit/
│   ├── integration/
│   └── k6/                        Load tests (100 VU, P95 < 200ms threshold)
├── docs/
│   ├── runbooks/                  On-call runbooks (Kafka lag, high cost, Qdrant unavailable)
│   └── security/                  SOC 2 gap analysis + pentest scope
├── scripts/                       One-off utility scripts
├── docker-compose.yml
├── pyproject.toml
├── PLAN.md                        Sprint roadmap
├── BRAND.md                       Design system — all UI decisions reference this
└── CLAUDE.md                      AI agent instructions for this codebase
```

---

## Security

- API keys stored as **PBKDF2-HMAC-SHA256 hashes** with a random 32-byte salt; the raw value is returned once at creation and never persisted
- Strict **per-org row isolation** — all queries are scoped by `organization_id`
- **GDPR right to erasure** — `DELETE /api/v1/organizations/{id}` cascades all data including Qdrant vectors and Neo4j nodes
- **Security headers** — full CSP, HSTS (production), X-Frame-Options DENY, Permissions-Policy
- **Circuit breakers** on all external API calls (OpenAI, Resend) — prevents cascade failures
- **Daily spend caps** enforced before any OpenAI call — configurable via `MAX_DAILY_SPEND_USD`
- SOC 2 gap analysis: `docs/security/soc2_gap_analysis.md`
- Penetration test scope: `docs/security/pentest_scope.md`

To report a vulnerability: **security@hallucin8.io**

---

## License

Private — © 2026 OPB AI Mastery Lab. All rights reserved.  
Not licensed for redistribution or use outside of authorised beta access.
