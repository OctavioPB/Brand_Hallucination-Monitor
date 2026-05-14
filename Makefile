.PHONY: help up down restart seed kafka-topics kafka-schemas monitoring test test-be test-fe lint format typecheck healthcheck logs clean

# Default target
help:
	@echo ""
	@echo "hallucin8 — development commands"
	@echo "================================="
	@echo "  make up          Start all core services (Postgres, Redis, Qdrant, Neo4j, Redpanda)"
	@echo "  make up-all      Start core + Airflow (requires --profile airflow)"
	@echo "  make down        Stop and remove containers"
	@echo "  make restart     down + up"
	@echo "  make seed        Seed initial data (brands, intent clusters)"
	@echo "  make test        Run all tests (backend + frontend)"
	@echo "  make test-be     Run Python tests only"
	@echo "  make test-fe     Run Next.js tests only"
	@echo "  make lint        Lint all code (ruff + eslint)"
	@echo "  make format      Auto-format all code (ruff + prettier)"
	@echo "  make typecheck   Run mypy + tsc"
	@echo "  make healthcheck Verify all services are live"
	@echo "  make logs        Tail all service logs"
	@echo "  make clean       Remove volumes + build artifacts"
	@echo ""

# ----------------------------------------------------------------
# Docker Compose
# ----------------------------------------------------------------
up:
	docker compose up -d
	@echo "✓ Core services started. Run 'make healthcheck' to verify."

up-all:
	docker compose --profile airflow up -d
	@echo "✓ All services started (including Airflow)."

monitoring:
	docker compose --profile monitoring up -d
	@echo "✓ Prometheus on http://localhost:9090  Grafana on http://localhost:3001 (admin/hallucin8)"

kafka-topics:
	bash infra/kafka/create_topics.sh

kafka-schemas:
	bash infra/kafka/register_schemas.sh

kafka-setup: kafka-topics kafka-schemas
	@echo "✓ Kafka topics and schemas ready."

down:
	docker compose --profile airflow --profile monitoring down

restart: down up

logs:
	docker compose logs -f

clean:
	docker compose --profile airflow down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	cd apps/dashboard && rm -rf .next out 2>/dev/null || true

# ----------------------------------------------------------------
# Database
# ----------------------------------------------------------------
migrate:
	cd apps/api && alembic upgrade head

migrate-down:
	cd apps/api && alembic downgrade -1

seed:
	python scripts/seed_data.py

# ----------------------------------------------------------------
# Tests
# ----------------------------------------------------------------
test: test-be test-fe

test-be:
	pytest tests/ -v --tb=short

test-fe:
	cd apps/dashboard && pnpm test

# ----------------------------------------------------------------
# Code quality
# ----------------------------------------------------------------
lint:
	ruff check apps/ tests/
	cd apps/dashboard && pnpm lint

format:
	ruff format apps/ tests/
	ruff check --fix apps/ tests/
	cd apps/dashboard && pnpm prettier --write "src/**/*.{ts,tsx,css}"

typecheck:
	mypy apps/api apps/workers
	cd apps/dashboard && pnpm tsc --noEmit

# ----------------------------------------------------------------
# Health
# ----------------------------------------------------------------
healthcheck:
	bash scripts/healthcheck.sh

# ----------------------------------------------------------------
# Dev servers (run in separate terminals)
# ----------------------------------------------------------------
api:
	cd apps/api && uvicorn main:app --reload --port 8000

dashboard:
	cd apps/dashboard && pnpm dev
