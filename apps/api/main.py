"""FastAPI application entrypoint."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import get_settings
from apps.api.database import engine
from apps.api.logging_config import configure_logging
from apps.api.middleware.request_id import RequestIDMiddleware
from apps.api.models.db import Base

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
# Middleware
# -----------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)


# -----------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------
@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/api/v1/status", tags=["meta"])
async def api_status() -> dict[str, str]:
    return {"version": "0.1.0", "status": "operational"}
