# hallucin8

**SGE Semantic Dominance & Brand Hallucination Monitor**

> *Your brand exists in the vector space of every AI. We tell you where you are, where you need to be, and what lies the models are telling about you.*

---

## Value Proposition

Every major AI model — ChatGPT, Gemini, Perplexity, Claude — has already formed an opinion about your brand. It's encoded in their latent space, shaped by the data they were trained on, and it influences every recommendation they give your potential customers. You have no visibility into it.

**hallucin8** gives brand and marketing teams the infrastructure to:

- **Detect hallucinations** before they reach customers — factual errors, competitor confusion, and negative sentiment drift in AI-generated content
- **Measure semantic proximity** between your brand and the concepts that drive purchase intent: reliability, innovation, market leadership, compliance, pricing value
- **Track competitor positioning** inside AI latent space, not just search rankings
- **Audit AI compliance** — a defensible, reportable record that your brand is being represented accurately
- **Get alerted** the moment perception shifts, with configurable thresholds and Slack/email delivery

This is **Brand Safety & AI Compliance** infrastructure, not SEO manipulation.

---

## How It Works

```
Brand mentions (RSS, Reddit, web)
        │
        ▼
  Kafka ingestion ──► dedup ──► enrichment ──► routing
        │
        ▼
  OpenAI Embeddings (text-embedding-3-small)
        │
        ▼
  Qdrant vector store ◄──────────────────────────────┐
        │                                             │
        ▼                                             │
  Neo4j knowledge graph          Airflow Vector ETL ──┘
  (Brand → Concept associations)
        │
        ▼
  Semantic Proximity Score (SPS) ── FastAPI ── Next.js Dashboard
        │
        ▼
  LLM Probing (GPT-4o-mini daily / Gemini 1.5 Pro weekly)
        │
        ▼
  Hallucination Detection ── Alert Engine ── Reports
```

### Core Concepts

**Semantic Proximity Score (SPS)** — a float `[0.0–1.0]` representing cosine similarity between a brand's embedding and a target concept vector (e.g. "reliable", "market leader"). Higher = stronger association in the model's latent space.

**Brand Hallucination** — when a probed LLM associates a brand with factually incorrect attributes, confuses it with a competitor, or generates unprompted negative sentiment. Detected by comparing LLM outputs against your brand manifest.

**Brand Manifest** — the ground truth you define: true attributes, false attributes, competitors to track, regulatory claims to avoid. All hallucination detection is relative to this manifest.

---

## Tech Stack

### Backend

| Layer | Technology | Version |
|---|---|---|
| API | FastAPI + Uvicorn | 0.111+ |
| ORM | SQLAlchemy 2 + Alembic | 2.0+ |
| Task queue | Celery + Redis | 5.4+ |
| Stream broker | Redpanda (Kafka-compatible) | v24.1 |
| Orchestration | Apache Airflow | 2.9.3 |
| Vector database | Qdrant | v1.9.4 |
| Knowledge graph | Neo4j | 5.20 |
| Cache | Redis | 7 |
| Relational DB | PostgreSQL | 16 |
| Connection pooler | PgBouncer | 1.22 (optional) |
| Language | Python | 3.12 |

### Frontend

| Layer | Technology | Version |
|---|---|---|
| Framework | Next.js (App Router) | 14.2 |
| UI | React | 18.3 |
| Charts | Recharts | 2.12 |
| Server state | TanStack Query | v5 |
| Client state | Zustand | 4.5 |
| Product tour | Shepherd.js | 11 (CDN) |
| Analytics | PostHog | JS snippet |
| Support chat | Intercom | SDK |
| Error tracking | Sentry | 8 |

### ML / AI

| Layer | Technology | Notes |
|---|---|---|
| Embeddings | OpenAI `text-embedding-3-small` | 1536-dim vectors |
| Daily probing | GPT-4o-mini | Cost-optimised daily scans |
| Weekly probing | Gemini 1.5 Pro | Higher-quality weekly deep scan |
| Sentiment | VADER | Lightweight lexicon baseline |
| Projection | scikit-learn t-SNE | 2D vector map visualisation |

### Infrastructure & Observability

| Layer | Technology |
|---|---|
| Containers | Docker + Docker Compose (dev) |
| CI/CD | GitHub Actions |
| Cloud (prod) | GCP — Cloud Run, Cloud Storage |
| Metrics | Prometheus + Grafana |
| Error tracking | Sentry (backend + frontend) |
| Backups | pg_dump + Neo4j APOC → GCS (daily) |
| Load testing | k6 |

---

## Prerequisites

- Docker Desktop 4.x (or Docker Engine + Compose v2)
- Python 3.12+
- Node.js 20+
- An [OpenAI API key](https://platform.openai.com/api-keys)

Optional (for full feature set):
- Gemini API key — weekly deep probing
- Resend API key — alert emails and onboarding sequence
- Slack webhook URL — alert notifications
- Sentry DSN — error tracking
- GCS bucket + service account — automated backups

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/opb-ai-lab/hallucin8.git
cd hallucin8
```

### 2. Configure environment variables

```bash
cp .env.example .env.local
```

Open `.env.local` and fill in at minimum:

```bash
OPENAI_API_KEY=sk-...          # Required for embeddings + LLM probing
JWT_SECRET=<strong-random>     # Required for API key signing
```

All other variables have working defaults for local development.

### 3. Install Python dependencies

```bash
pip install -e ".[dev]"
```

### 4. Install frontend dependencies

```bash
cd apps/dashboard && npm install
```

---

## Quick Start

### Start the core infrastructure

```bash
docker-compose up -d
```

This starts: PostgreSQL 16, Redis 7, Qdrant, Neo4j 5, Redpanda (Kafka), and Redpanda Console.

### Run database migrations

```bash
cd apps/api && alembic upgrade head
```

### Start the API server

```bash
cd apps/api && uvicorn main:app --reload --port 8000
```

API docs are available at [http://localhost:8000/api/docs](http://localhost:8000/api/docs).

### Start the dashboard

```bash
cd apps/dashboard && npm run dev
```

Dashboard is available at [http://localhost:3000](http://localhost:3000).

### Seed demo data (optional)

```bash
curl -X POST http://localhost:8000/api/v1/onboarding/demo/seed
```

This creates a fictional `AcmeCorp` brand pre-populated with attributes, competitors, and a brand manifest — ready to explore without any setup.

### Trigger your first scan

```bash
# 1. Create an org + get your API key
curl -X POST http://localhost:8000/api/v1/onboarding/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "you@company.com", "org_name": "My Company"}'

# 2. Trigger a scan (replace <api-key> and <brand-id>)
curl -X POST http://localhost:8000/api/v1/scan-jobs \
  -H "X-API-Key: <api-key>" \
  -H "Content-Type: application/json" \
  -d '{"brand_id": "<brand-id>", "job_type": "llm_probe"}'
```

---

## Optional Profiles

### Start with Airflow (Vector ETL orchestration)

```bash
docker-compose --profile airflow up -d
```

Airflow UI: [http://localhost:8085](http://localhost:8085) · credentials: `admin / admin`

DAGs available:
- `dag_vector_etl` — daily embedding pipeline
- `dag_weekly_report` — Sunday 08:00 UTC brand safety report
- `dag_backup` — daily 02:00 UTC PostgreSQL + Neo4j → GCS
- `dag_onboarding_emails` — daily D+3/D+7 email sequence

### Start with monitoring (Prometheus + Grafana)

```bash
docker-compose --profile monitoring up -d
```

- Prometheus: [http://localhost:9090](http://localhost:9090)
- Grafana: [http://localhost:3001](http://localhost:3001) · credentials: `admin / admin`

Dashboards pre-loaded: Kafka consumer lag, embedding costs, Airflow DAG health.

### Start with PgBouncer (production connection pooling)

```bash
docker-compose --profile pgbouncer up -d
# Use port 5433 instead of 5432 in DATABASE_URL
```

### Start everything

```bash
docker-compose --profile airflow --profile monitoring up -d
```

---

## Development Commands

```bash
# Run tests
pytest tests/ -v --cov=apps/api

# Lint + format (Python)
ruff check . && ruff format .

# Type check
mypy apps/api apps/workers

# Frontend tests
cd apps/dashboard && npm run test

# Frontend lint
cd apps/dashboard && npm run lint

# Generate a new Alembic migration
cd apps/api && alembic revision --autogenerate -m "your description"

# Run the k6 load test (requires k6 installed)
k6 run tests/k6/load_test.js

# Enable Qdrant scalar quantization (reduces storage 4x)
python scripts/init_qdrant_quantization.py
```

---

## Service URLs (local dev)

| Service | URL | Notes |
|---|---|---|
| Dashboard | http://localhost:3000 | Next.js frontend |
| API | http://localhost:8000 | FastAPI backend |
| API docs | http://localhost:8000/api/docs | Swagger UI |
| Qdrant UI | http://localhost:6333/dashboard | Vector DB browser |
| Neo4j Browser | http://localhost:7474 | Graph explorer · `neo4j / hallucin8pass` |
| Redpanda Console | http://localhost:8080 | Kafka topic inspector |
| Airflow | http://localhost:8085 | DAG orchestration · `admin / admin` |
| Prometheus | http://localhost:9090 | Metrics |
| Grafana | http://localhost:3001 | Dashboards · `admin / admin` |

---

## Project Structure

```
hallucin8/
├── apps/
│   ├── api/               FastAPI backend (Python 3.12)
│   │   ├── models/        SQLAlchemy ORM models
│   │   ├── routers/       API endpoints (/api/v1/...)
│   │   ├── services/      Business logic (cost guard, circuit breaker, reports...)
│   │   ├── middleware/     Request ID, metrics, security headers
│   │   ├── migrations/    Alembic migrations (001–009)
│   │   └── auth/          API key management + org context
│   ├── dashboard/         Next.js 14 frontend
│   │   └── src/
│   │       ├── app/       App Router pages (dashboard, admin, auth, changelog...)
│   │       ├── components/ Reusable UI components
│   │       ├── hooks/     TanStack Query hooks
│   │       └── lib/       brand-tokens, api-client, posthog, feature-flags
│   └── workers/           Celery async workers
│       ├── consumers/     Kafka consumers (dedup, enrichment, routing)
│       └── tasks/         Celery tasks (scan, embedding)
├── infra/
│   ├── airflow/dags/      Airflow DAG definitions
│   ├── kafka/             Topic configs + Avro schemas
│   ├── neo4j/             Cypher queries + schema
│   ├── monitoring/        Prometheus config + Grafana dashboards
│   └── vector-db/         Qdrant collection configs
├── ml/
│   ├── embeddings/        Embedding service (OpenAI + circuit breaker + cost guard)
│   ├── clustering/        t-SNE / UMAP projection
│   ├── hallucination/     Hallucination detection models
│   └── scoring/           SPS calculation
├── tests/
│   ├── unit/
│   ├── integration/
│   └── k6/                Load tests (100 VU, P95 < 200ms threshold)
├── docs/
│   ├── runbooks/          On-call runbooks (Kafka lag, high cost, Qdrant unavailable)
│   └── security/          SOC 2 gap analysis + pentest scope
├── scripts/               One-off utility scripts
├── docker-compose.yml
├── pyproject.toml
├── PLAN.md                Sprint-by-sprint build roadmap
├── BRAND.md               Design system tokens (all UI decisions reference this)
└── CLAUDE.md              AI agent instructions for this codebase
```

---

## Security

- All API keys are stored as **bcrypt hashes**; the raw value is returned once at creation and never stored
- Strict **per-org Row Level Security** — all queries are scoped by `organization_id`
- **GDPR right to erasure** — `DELETE /api/v1/organizations/{id}` cascades all data including Qdrant vectors and Neo4j nodes
- **Security headers** — full CSP, HSTS (production), X-Frame-Options DENY, Permissions-Policy
- **Circuit breakers** on all external API calls (OpenAI, Slack, Resend) — prevents cascade failures
- **Daily spend caps** enforced before any OpenAI call (configurable via `MAX_DAILY_SPEND_USD`)
- SOC 2 gap analysis: `docs/security/soc2_gap_analysis.md`
- Penetration test scope defined: `docs/security/pentest_scope.md`

To report a security vulnerability, email **security@hallucin8.io**.

---

## License

Private — © 2026 OPB AI Mastery Lab. All rights reserved.
Not licensed for redistribution or use outside of authorised beta access.
