# CLAUDE.md — SGE Semantic Dominance & Brand Hallucination Monitor

> This file is the primary guide for Claude Code agents working on this codebase.
> Read it fully before writing any code, creating files, or making architectural decisions.

---

## 🧭 Project Identity

**Name:** SGE Semantic Dominance & Brand Hallucination Monitor
**Codename:** `hallucin8`
**Purpose:** Monitor, audit, and influence how Large Language Models (ChatGPT, Gemini, Perplexity, etc.)
perceive and recommend a brand versus its competitors — positioning this as
**Brand Safety & AI Compliance infrastructure**, not manipulation.

**Core Value Proposition:**
> "Your brand exists in the vector space of every AI. We tell you where you are, where you need to be,
> and what lies the models are telling about you."

---

## 🗂️ Repository Structure

```
hallucin8/
├── CLAUDE.md                  ← You are here
├── PLAN.md                    ← Sprint roadmap
├── BRAND.md                   ← ⚠️ ALL UI/UX decisions MUST reference this file
│
├── apps/
│   ├── api/                   ← FastAPI backend (Python 3.12)
│   ├── dashboard/             ← Next.js 14 + App Router frontend
│   └── workers/               ← Celery async task workers
│
├── infra/
│   ├── kafka/                 ← Kafka topics, schemas, consumer configs
│   ├── airflow/               ← DAGs for Vector ETL pipeline
│   ├── neo4j/                 ← Knowledge graph schemas and Cypher queries
│   └── vector-db/             ← Qdrant collections and index configs
│
├── ml/
│   ├── embeddings/            ← Embedding generation (text-embedding-3-small)
│   ├── clustering/            ← t-SNE / UMAP projection pipelines
│   ├── hallucination/         ← Brand hallucination detection models
│   └── scoring/               ← Semantic proximity scoring logic
│
├── data/
│   ├── seeds/                 ← Initial brand/competitor seed data
│   ├── fixtures/              ← Test fixtures for local dev
│   └── schemas/               ← Pydantic models, Avro schemas
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/                   ← One-off utility scripts
├── docs/                      ← Architecture Decision Records (ADRs)
├── docker-compose.yml
└── pyproject.toml
```

---

## 🖌️ UI & Design Decisions

> **⚠️ CRITICAL: For ALL frontend, component, styling, color, typography, animation,
> and layout decisions — consult [`BRAND.md`](./BRAND.md) first.**

This includes but is not limited to:
- Color palette, gradients, and semantic color tokens
- Typography scale, font families, and weight conventions
- Spacing and layout grid system
- Component naming conventions (Button variants, Card types, Badge styles)
- Data visualization color schemes (scatter plots, heatmaps, graphs)
- Dark mode specifications
- Icon set and illustration style
- Loading states, skeleton screens, and animation easing
- Responsive breakpoints
- Tone of voice for UI copy (labels, empty states, tooltips, error messages)

**Never hardcode hex values, font names, or spacing values without checking BRAND.md.**
Use the design tokens exported from BRAND.md as CSS variables or Tailwind config extensions.

---

## 🏗️ Tech Stack

### Backend
| Layer | Technology | Notes |
|---|---|---|
| API | FastAPI 0.111+ | Async, OpenAPI auto-docs |
| Task Queue | Celery + Redis | Async embedding jobs |
| Stream Ingestion | Apache Kafka | Brand mention pipeline |
| Orchestration | Apache Airflow 2.9 | Vector ETL DAGs |
| Vector DB | Qdrant | Cosine similarity queries |
| Knowledge Graph | Neo4j 5.x | Semantic relationship store |
| Cache | Redis 7 | Embedding cache, rate limits |
| ORM | SQLAlchemy 2 + Alembic | Relational metadata |
| Auth | Supabase Auth / JWT | |

### Frontend
| Layer | Technology | Notes |
|---|---|---|
| Framework | Next.js 14 (App Router) | React Server Components |
| Styling | Tailwind CSS + tokens from BRAND.md | See BRAND.md |
| Charts | Recharts + custom D3 hooks | Vector scatter plots |
| State | Zustand | Client state |
| API Layer | TanStack Query v5 | Server state, caching |
| 3D Viz | Three.js (optional, S3+) | 3D vector space map |

### ML / AI
| Layer | Technology | Notes |
|---|---|---|
| Embeddings | OpenAI `text-embedding-3-small` | 1536-dim vectors |
| LLM Probing | OpenAI GPT-4o / Gemini 1.5 | Brand perception queries |
| Clustering | scikit-learn (t-SNE), umap-learn | Projection to 2D/3D |
| Graph ML | PyTorch Geometric (optional) | GNN hallucination scoring |

### Infrastructure
| Layer | Technology |
|---|---|
| Containers | Docker + Docker Compose (dev), Kubernetes (prod) |
| CI/CD | GitHub Actions |
| Cloud | GCP (primary) — Cloud Run, GKE, BigQuery |
| Monitoring | Grafana + Prometheus |
| Secrets | GCP Secret Manager / `.env.local` (dev only) |

---

## 🧪 Development Commands

```bash
# Start full local stack
docker-compose up -d

# Backend API (hot reload)
uvicorn apps.api.main:app --reload --port 8000

# Frontend dev server
cd apps/dashboard && npm run dev

# Run Airflow locally
cd infra/airflow && astro dev start

# Run tests
pytest tests/ -v --cov=apps/api
cd apps/dashboard && npm run test

# Lint & format
ruff check . && ruff format .
cd apps/dashboard && npm run lint

# Generate new Alembic migration
alembic revision --autogenerate -m "description"

# Run embedding pipeline manually
python scripts/run_embedding_job.py --brand "AcmeCorp" --keywords "hr software,startup,payroll"
```

---

## 🔑 Environment Variables

All secrets live in `.env.local` (never committed). Copy from `.env.example`.

```bash
# Required
OPENAI_API_KEY=
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost/hallucin8

# Optional (for LLM probing)
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
PERPLEXITY_API_KEY=
```

---

## 🧠 Core Domain Concepts

Understanding these is mandatory before touching any ML or data code.

### Semantic Proximity Score (SPS)
A float `[0.0 – 1.0]` representing cosine similarity between a brand's embedding
and a target concept vector (e.g., "reliable", "market leader", "affordable").
Higher = stronger association in the model's latent space.

### Brand Hallucination
When a probed LLM associates a brand with:
- Factually incorrect attributes (e.g., claims it has features it doesn't)
- Competitor confusion (e.g., conflates Brand A with Brand B)
- Negative sentiment drift (unprompted negative associations)

Detected by comparing LLM-probed outputs against a ground-truth brand attributes manifest.

### Vector ETL Pipeline
1. **Extract** — Kafka consumers pull brand mentions, reviews, articles
2. **Transform** — OpenAI Embeddings API generates vectors; cosine distances calculated
3. **Load** — Vectors stored in Qdrant; relationships written to Neo4j

### Knowledge Graph Schema (Neo4j)
```cypher
(Brand)-[:ASSOCIATED_WITH {score: float, source: string}]->(Concept)
(Brand)-[:COMPETES_WITH]->(Brand)
(Brand)-[:HALLUCINATED_AS {model: string, confidence: float}]->(Attribute)
(Concept)-[:BELONGS_TO_CLUSTER]->(IntentCluster)
```

### Intent Clusters
Pre-defined semantic buckets derived from purchase-intent research:
`["reliability", "innovation", "pricing_value", "market_leadership", "compliance", "support_quality"]`

---

## 📐 Coding Standards

### Python
- Python 3.12+, strict type hints everywhere (`mypy --strict`)
- Pydantic v2 for all data models — no raw dicts crossing layer boundaries
- Async-first: `async def` for all I/O bound functions
- Ruff for linting and formatting (replaces Black + isort + flake8)
- Docstrings: Google style for public functions
- No `print()` — use `structlog` with JSON output

### TypeScript / React
- TypeScript strict mode, no `any`
- Functional components only, no class components
- Co-locate tests with components (`Component.test.tsx`)
- All UI tokens (colors, spacing, fonts) imported from `@/lib/brand-tokens`
  which is generated from **BRAND.md**
- No inline styles — Tailwind utility classes only, extended via brand config

### API Design
- REST for CRUD operations; Server-Sent Events (SSE) for real-time score streaming
- All endpoints return `{ data, meta, error }` envelope
- Versioned: `/api/v1/...`
- Rate limit headers always present

### Git Conventions
```
feat(scope): short description
fix(scope): short description
chore(scope): short description
docs(scope): short description
```
Scopes: `api`, `dashboard`, `ml`, `kafka`, `airflow`, `neo4j`, `infra`

---

## 🚫 Hard Rules (Never Break These)

1. **Never commit API keys or secrets** — use `.env.local` + Secret Manager
2. **Never store raw PII** in Qdrant or Neo4j — hash brand mentions before storage
3. **Never expose competitor raw data** to the wrong tenant — enforce strict RLS
4. **Never sell or describe this as "manipulation"** in UI copy, docs, or APIs —
   always frame as "Brand Safety", "AI Compliance", or "Semantic Audit"
5. **Never hardcode brand colors, fonts, or design values** — reference BRAND.md tokens
6. **Never run embedding jobs on the main thread** — always enqueue via Celery
7. **Never query Neo4j with string-interpolated Cypher** — use parameterized queries

---

## 🧩 Key Architectural Decisions

| Decision | Choice | Reason |
|---|---|---|
| Vector DB | Qdrant over Pinecone | Self-hostable, lower cost at scale |
| Graph DB | Neo4j over DynamoDB | Native Cypher for semantic relationship queries |
| Embedding Model | text-embedding-3-small | Cost/performance tradeoff at high volume |
| Stream Processing | Kafka over SQS | Multi-consumer fan-out for parallel pipelines |
| Frontend | Next.js App Router | RSC for dashboard perf; SEO for marketing pages |
| Auth | Supabase | Fast setup, RLS built-in for multi-tenant |

Full ADRs in `docs/adr/`.

---

## 🔗 Related Files

| File | Purpose |
|---|---|
| [`PLAN.md`](./PLAN.md) | Sprint-by-sprint build roadmap |
| [`BRAND.md`](./BRAND.md) | ⚠️ UI/UX design system — required for all frontend work |
| `docs/adr/` | Architecture Decision Records |
| `infra/airflow/dags/` | Vector ETL pipeline definitions |
| `ml/hallucination/README.md` | Hallucination detection model docs |
| `data/schemas/` | Canonical Pydantic + Avro data models |
