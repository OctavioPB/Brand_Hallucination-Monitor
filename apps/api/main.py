"""FastAPI application entrypoint."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import get_settings
from apps.api.database import engine
from apps.api.logging_config import configure_logging
from apps.api.middleware.error_handler import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from apps.api.middleware.metrics import setup_metrics
from apps.api.middleware.request_id import RequestIDMiddleware
from apps.api.models.db import Base
from apps.api.middleware.security_headers import SecurityHeadersMiddleware
from apps.api.routers import (
    admin,
    alert_rules,
    alerts,
    auth,
    brands,
    competitors,
    costs,
    graph,
    mentions,
    onboarding,
    organizations,
    reports,
    scan_jobs,
    vector_map,
)

configure_logging()
logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting hallucin8 API", env=settings.app_env)

    async with engine.begin() as conn:
        # In production, use Alembic migrations — not create_all.
        if not settings.is_production:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables verified (dev mode)")

    # Sentry (Sprint 9) — init before first request
    if settings.sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            environment=settings.app_env,
        )
        logger.info("Sentry initialized", env=settings.app_env)

    yield

    logger.info("Shutting down hallucin8 API")
    await engine.dispose()


app = FastAPI(
    title="hallucin8 API",
    description="SGE Semantic Dominance & Brand Hallucination Monitor",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# -----------------------------------------------------------------------
# Middleware (order matters — outermost wraps innermost)
# -----------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware, is_production=settings.is_production)

# Prometheus metrics — must be called after app is created, before first request
setup_metrics(app)

# -----------------------------------------------------------------------
# Exception handlers — standardized error envelope
# -----------------------------------------------------------------------
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# -----------------------------------------------------------------------
# Routers
# -----------------------------------------------------------------------
app.include_router(mentions.router)
app.include_router(graph.router)
app.include_router(costs.router)
app.include_router(brands.router)
app.include_router(competitors.router)
app.include_router(alerts.router)
app.include_router(alert_rules.router)
app.include_router(scan_jobs.router)
app.include_router(vector_map.router)
app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(reports.compliance_router)
app.include_router(onboarding.router)
app.include_router(organizations.router)
app.include_router(admin.router)


# -----------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------
@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/api/v1/status", tags=["meta"])
async def api_status() -> dict[str, str]:
    return {"version": "0.1.0", "status": "operational"}
