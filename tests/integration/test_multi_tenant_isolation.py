"""Integration tests: Org A cannot read Org B's data.

Uses an in-memory SQLite database (aiosqlite) — no PostgreSQL required.
Each test creates two organizations with their own brands and verifies
that all endpoints enforce organization_id isolation.

The tests mock the get_org_context dependency so they don't need Redis
or JWT infrastructure. This is the correct pattern for testing RLS:
inject a known OrgContext and verify the query filter works.
"""
from __future__ import annotations

import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# SQLite compatibility: teach the SQLite DDL compiler to handle
# PostgreSQL-specific column types used in the ORM models.
# These patches are test-only and are applied once at module import time.
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # type: ignore[attr-defined]

SQLiteTypeCompiler.visit_JSONB = SQLiteTypeCompiler.visit_JSON  # type: ignore[attr-defined]
SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "VARCHAR(36)"  # type: ignore[attr-defined]
SQLiteTypeCompiler.visit_ARRAY = lambda self, type_, **kw: "TEXT"  # type: ignore[attr-defined]

from apps.api.auth.context import OrgContext, get_org_context
from apps.api.database import Base, get_db
from apps.api.models.brand import BrandORM
from apps.api.models.probe_result import ProbeResultORM
from apps.api.models.sps_score import SPSScoreORM
from apps.api.models.db import AlertORM

# Import all ORM models so metadata is complete before create_all
import apps.api.models.db  # noqa: F401

_SQLITE_URL = "sqlite+aiosqlite:///:memory:"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(_SQLITE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the FastAPI app with SQLite session override."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    from apps.api.main import app
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


def _org_ctx(org_id: str, role: str = "admin") -> OrgContext:
    return OrgContext(organization_id=org_id, user_id=f"user-{org_id}", role=role)


def _override_auth(client, org_id: str, role: str = "admin"):
    """Override get_org_context for the next request."""
    from apps.api.main import app
    app.dependency_overrides[get_org_context] = lambda: _org_ctx(org_id, role)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

async def _create_brand(db: AsyncSession, org_id: str, name: str, slug: str) -> BrandORM:
    brand = BrandORM(
        id=uuid.uuid4(),
        organization_id=org_id,
        name=name,
        slug=slug,
        manifest=None,
    )
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return brand


# ---------------------------------------------------------------------------
# Tests: Brand endpoints
# ---------------------------------------------------------------------------

class TestBrandIsolation:
    async def test_list_brands_returns_only_own_org(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /brands returns only brands belonging to the caller's organization."""
        brand_a = await _create_brand(db_session, "org-a", "BrandA", "brand-a")
        await _create_brand(db_session, "org-b", "BrandB", "brand-b")

        _override_auth(client, "org-a")
        resp = await client.get("/api/v1/brands")
        assert resp.status_code == 200
        names = [b["name"] for b in resp.json()]
        assert "BrandA" in names
        assert "BrandB" not in names

    async def test_get_brand_returns_404_for_other_org(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /brands/{id} for a brand owned by Org B returns 404 to Org A."""
        brand_b = await _create_brand(db_session, "org-b", "BrandB", "brand-b-get")

        _override_auth(client, "org-a")
        resp = await client.get(f"/api/v1/brands/{brand_b.id}")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"

    async def test_create_brand_scoped_to_caller_org(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /brands creates a brand under the caller's organization_id."""
        _override_auth(client, "org-c")
        resp = await client.post(
            "/api/v1/brands",
            json={"organization_id": "org-ignored", "name": "OrgC Brand", "slug": "orgc-brand"},
        )
        assert resp.status_code == 201
        assert resp.json()["organization_id"] == "org-c"

    async def test_manifest_update_blocked_for_other_org(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        brand_b = await _create_brand(db_session, "org-b", "BrandB", "brand-b-manifest")

        _override_auth(client, "org-a")
        resp = await client.put(
            f"/api/v1/brands/{brand_b.id}/manifest",
            json={"true_attributes": [], "false_attributes": [], "competitor_list": [], "regulatory_claims_to_avoid": []},
        )
        assert resp.status_code == 404

    async def test_sps_scores_blocked_for_other_org(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        brand_b = await _create_brand(db_session, "org-b", "BrandB", "brand-b-sps")

        _override_auth(client, "org-a")
        resp = await client.get(f"/api/v1/brands/{brand_b.id}/sps")
        assert resp.status_code == 404

    async def test_hallucinations_blocked_for_other_org(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        brand_b = await _create_brand(db_session, "org-b", "BrandB", "brand-b-hall")

        _override_auth(client, "org-a")
        resp = await client.get(f"/api/v1/brands/{brand_b.id}/hallucinations")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Alert endpoints
# ---------------------------------------------------------------------------

class TestAlertIsolation:
    async def _seed_alert(self, db: AsyncSession, org_id: str) -> AlertORM:
        brand = await _create_brand(db, org_id, f"Brand-{org_id}", f"brand-{org_id}-al")
        alert = AlertORM(
            id=uuid.uuid4(),
            organization_id=org_id,
            brand_id=brand.id,
            severity="HIGH",
            alert_type="hallucination",
            message="Test alert",
            acknowledged=False,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        return alert

    async def test_list_alerts_returns_only_own_org(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await self._seed_alert(db_session, "org-alert-a")
        await self._seed_alert(db_session, "org-alert-b")

        _override_auth(client, "org-alert-a")
        resp = await client.get("/api/v1/alerts")
        assert resp.status_code == 200
        orgs = {a["organization_id"] for a in resp.json()}
        assert orgs == {"org-alert-a"}

    async def test_acknowledge_blocked_for_other_org(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        alert_b = await self._seed_alert(db_session, "org-alert-b2")

        _override_auth(client, "org-alert-a2")
        resp = await client.patch(f"/api/v1/alerts/{alert_b.id}/acknowledge")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Competitor endpoints
# ---------------------------------------------------------------------------

class TestCompetitorIsolation:
    async def test_list_competitors_blocked_for_other_org(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        brand_b = await _create_brand(db_session, "org-comp-b", "Brand", "brand-comp-b")

        _override_auth(client, "org-comp-a")
        resp = await client.get(f"/api/v1/brands/{brand_b.id}/competitors")
        assert resp.status_code == 404

    async def test_add_competitor_blocked_for_other_org(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        brand_b = await _create_brand(db_session, "org-comp-b2", "Brand", "brand-comp-b2")

        _override_auth(client, "org-comp-a2")
        resp = await client.post(
            f"/api/v1/brands/{brand_b.id}/competitors",
            json={"brand_id": str(brand_b.id), "competitor_name": "RivalCo"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Error envelope shape
# ---------------------------------------------------------------------------

class TestErrorEnvelope:
    async def test_404_has_error_envelope(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        _override_auth(client, "org-error")
        resp = await client.get(f"/api/v1/brands/{uuid.uuid4()}")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]
        assert body["error"]["code"] == "NOT_FOUND"

    async def test_422_validation_error_has_envelope(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        _override_auth(client, "org-error2")
        resp = await client.post("/api/v1/brands", json={"invalid_field": "x"})
        assert resp.status_code == 422
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "details" in body["error"]


# ---------------------------------------------------------------------------
# Tests: Role enforcement
# ---------------------------------------------------------------------------

class TestRoleEnforcement:
    async def test_viewer_cannot_create_api_key(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        _override_auth(client, "org-role", role="viewer")
        resp = await client.post(
            "/api/v1/auth/api-keys",
            json={"name": "test-key", "role": "analyst"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"

    async def test_admin_can_create_api_key(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        _override_auth(client, "org-role-admin", role="admin")
        resp = await client.post(
            "/api/v1/auth/api-keys",
            json={"name": "test-key", "role": "analyst"},
        )
        assert resp.status_code == 201
        assert "raw_key" in resp.json()
        assert resp.json()["raw_key"].startswith("hk_")
