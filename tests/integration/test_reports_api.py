"""Integration tests for the reports + alert-rules API endpoints.

Uses in-memory SQLite with the same SQLite type-patching pattern as
test_multi_tenant_isolation.py. No PostgreSQL or PDF rendering required.
"""
from __future__ import annotations

import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# SQLite type patches (same pattern as test_multi_tenant_isolation.py)
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # type: ignore[attr-defined]

SQLiteTypeCompiler.visit_JSONB = SQLiteTypeCompiler.visit_JSON  # type: ignore[attr-defined]
SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "VARCHAR(36)"  # type: ignore[attr-defined]
SQLiteTypeCompiler.visit_ARRAY = lambda self, type_, **kw: "TEXT"  # type: ignore[attr-defined]
SQLiteTypeCompiler.visit_LargeBinary = lambda self, type_, **kw: "BLOB"  # type: ignore[attr-defined]

from apps.api.auth.context import OrgContext, get_org_context
from apps.api.database import Base, get_db
from apps.api.main import app
from apps.api.models.brand import BrandORM
from apps.api.models.db import AlertORM
from apps.api.models.report import AlertRuleORM, ReportORM
from apps.api.models.sps_score import SPSScoreORM

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
ORG_A = "org_alpha"
ORG_B = "org_beta"


@pytest_asyncio.fixture(scope="module")
async def engine():
    e = create_async_engine(TEST_DB_URL, echo=False)
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await e.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


def _make_org_ctx(org_id: str, role: str = "admin") -> OrgContext:
    return OrgContext(organization_id=org_id, role=role, api_key_id=None)


@pytest_asyncio.fixture
async def client_a(db):
    async def _override_db():
        yield db

    async def _override_ctx():
        return _make_org_ctx(ORG_A)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_org_context] = _override_ctx

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_b(db):
    async def _override_db():
        yield db

    async def _override_ctx():
        return _make_org_ctx(ORG_B)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_org_context] = _override_ctx

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

async def _seed_brand(db: AsyncSession, org_id: str, name: str = "TestBrand") -> BrandORM:
    brand = BrandORM(
        id=uuid.uuid4(),
        organization_id=org_id,
        name=name,
        slug=f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}",
        manifest={"true_attributes": ["reliable"], "false_attributes": [], "competitor_list": [], "regulatory_claims_to_avoid": []},
    )
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return brand


async def _seed_report(db: AsyncSession, org_id: str, brand_id: uuid.UUID) -> ReportORM:
    from datetime import date
    report = ReportORM(
        id=uuid.uuid4(),
        organization_id=org_id,
        brand_id=brand_id,
        report_type="weekly",
        title="Test Report",
        content_json={"brand_name": "TestBrand", "total_probes": 0},
        week_start=date.today(),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def _seed_alert_rule(
    db: AsyncSession, org_id: str, brand_id: uuid.UUID
) -> AlertRuleORM:
    rule = AlertRuleORM(
        id=uuid.uuid4(),
        organization_id=org_id,
        brand_id=brand_id,
        rule_type="sps_threshold",
        cluster_slug="reliability",
        threshold=0.60,
        severity="HIGH",
        is_active=True,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


# ---------------------------------------------------------------------------
# Reports API tests
# ---------------------------------------------------------------------------

class TestListReports:
    async def test_empty_list_for_new_org(self, client_a) -> None:
        resp = await client_a.get("/api/v1/reports")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_own_reports(self, client_a, db) -> None:
        brand = await _seed_brand(db, ORG_A)
        await _seed_report(db, ORG_A, brand.id)

        resp = await client_a.get("/api/v1/reports")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["organization_id"] == ORG_A

    async def test_org_isolation(self, client_a, client_b, db) -> None:
        brand_b = await _seed_brand(db, ORG_B, "BrandB")
        await _seed_report(db, ORG_B, brand_b.id)

        # Org A should NOT see Org B's report
        resp = await client_a.get("/api/v1/reports")
        assert resp.status_code == 200
        ids = [r["organization_id"] for r in resp.json()]
        assert ORG_B not in ids


class TestGetReport:
    async def test_returns_404_for_unknown_id(self, client_a) -> None:
        resp = await client_a.get(f"/api/v1/reports/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_returns_404_for_other_org_report(self, client_a, client_b, db) -> None:
        brand_b = await _seed_brand(db, ORG_B, "BrandB2")
        report_b = await _seed_report(db, ORG_B, brand_b.id)

        # Org A tries to read Org B's report
        resp = await client_a.get(f"/api/v1/reports/{report_b.id}")
        assert resp.status_code == 404

    async def test_returns_report_with_content_json(self, client_a, db) -> None:
        brand = await _seed_brand(db, ORG_A, "AcmeCorp")
        report = await _seed_report(db, ORG_A, brand.id)

        resp = await client_a.get(f"/api/v1/reports/{report.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert "content_json" in body
        assert body["report_type"] == "weekly"


class TestDownloadPDF:
    async def test_404_when_no_pdf(self, client_a, db) -> None:
        brand = await _seed_brand(db, ORG_A, "NoPDFBrand")
        report = await _seed_report(db, ORG_A, brand.id)

        resp = await client_a.get(f"/api/v1/reports/{report.id}/download")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Alert Rules API tests
# ---------------------------------------------------------------------------

class TestCreateAlertRule:
    async def test_create_sps_threshold_rule(self, client_a, db) -> None:
        brand = await _seed_brand(db, ORG_A, "RuleBrand")
        payload = {
            "brand_id": str(brand.id),
            "rule_type": "sps_threshold",
            "cluster_slug": "reliability",
            "threshold": 0.55,
            "severity": "HIGH",
        }
        resp = await client_a.post("/api/v1/alert-rules", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["rule_type"] == "sps_threshold"
        assert body["threshold"] == pytest.approx(0.55)
        assert body["is_active"] is True

    async def test_create_competitor_rank_rule(self, client_a, db) -> None:
        brand = await _seed_brand(db, ORG_A, "CompBrand")
        payload = {
            "brand_id": str(brand.id),
            "rule_type": "competitor_rank",
            "cluster_slug": "innovation",
            "competitor_name": "RivalCorp",
            "severity": "CRITICAL",
        }
        resp = await client_a.post("/api/v1/alert-rules", json=payload)
        assert resp.status_code == 201
        assert resp.json()["competitor_name"] == "RivalCorp"

    async def test_rejects_invalid_rule_type(self, client_a, db) -> None:
        brand = await _seed_brand(db, ORG_A, "BadRuleBrand")
        payload = {
            "brand_id": str(brand.id),
            "rule_type": "not_a_real_type",
            "cluster_slug": "reliability",
            "threshold": 0.5,
        }
        resp = await client_a.post("/api/v1/alert-rules", json=payload)
        assert resp.status_code == 422

    async def test_rejects_sps_threshold_without_threshold_value(self, client_a, db) -> None:
        brand = await _seed_brand(db, ORG_A, "MissingThreshBrand")
        payload = {
            "brand_id": str(brand.id),
            "rule_type": "sps_threshold",
            "cluster_slug": "reliability",
            # threshold missing → should fail
        }
        resp = await client_a.post("/api/v1/alert-rules", json=payload)
        assert resp.status_code == 422


class TestListAlertRules:
    async def test_org_isolation(self, client_a, client_b, db) -> None:
        brand_b = await _seed_brand(db, ORG_B, "IsoRuleBrand")
        await _seed_alert_rule(db, ORG_B, brand_b.id)

        resp = await client_a.get("/api/v1/alert-rules")
        assert resp.status_code == 200
        org_ids = [r["organization_id"] for r in resp.json()]
        assert ORG_B not in org_ids


class TestUpdateAlertRule:
    async def test_deactivate_rule(self, client_a, db) -> None:
        brand = await _seed_brand(db, ORG_A, "UpdateRuleBrand")
        rule = await _seed_alert_rule(db, ORG_A, brand.id)

        resp = await client_a.put(
            f"/api/v1/alert-rules/{rule.id}",
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_cannot_update_other_org_rule(self, client_a, client_b, db) -> None:
        brand_b = await _seed_brand(db, ORG_B, "OtherOrgRuleBrand")
        rule_b = await _seed_alert_rule(db, ORG_B, brand_b.id)

        resp = await client_a.put(
            f"/api/v1/alert-rules/{rule_b.id}",
            json={"is_active": False},
        )
        assert resp.status_code == 404


class TestDeleteAlertRule:
    async def test_delete_own_rule(self, client_a, db) -> None:
        brand = await _seed_brand(db, ORG_A, "DeleteRuleBrand")
        rule = await _seed_alert_rule(db, ORG_A, brand.id)

        resp = await client_a.delete(f"/api/v1/alert-rules/{rule.id}")
        assert resp.status_code == 204

    async def test_cannot_delete_other_org_rule(self, client_a, client_b, db) -> None:
        brand_b = await _seed_brand(db, ORG_B, "DelOtherBrand")
        rule_b = await _seed_alert_rule(db, ORG_B, brand_b.id)

        resp = await client_a.delete(f"/api/v1/alert-rules/{rule_b.id}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Compliance export
# ---------------------------------------------------------------------------

class TestComplianceExport:
    async def test_404_for_other_org_brand(self, client_a, client_b, db) -> None:
        brand_b = await _seed_brand(db, ORG_B, "ComplianceBrand")
        resp = await client_a.get(f"/api/v1/brands/{brand_b.id}/compliance-export")
        assert resp.status_code == 404

    async def test_streams_jsonl_content_type(self, client_a, db) -> None:
        brand = await _seed_brand(db, ORG_A, "ComplianceOwn")
        resp = await client_a.get(f"/api/v1/brands/{brand.id}/compliance-export")
        assert resp.status_code == 200
        assert "ndjson" in resp.headers["content-type"] or "jsonl" in resp.headers.get("content-disposition", "")

    async def test_first_line_is_brand_manifest(self, client_a, db) -> None:
        import json as _json

        brand = await _seed_brand(db, ORG_A, "ManifestBrand")
        resp = await client_a.get(f"/api/v1/brands/{brand.id}/compliance-export")
        assert resp.status_code == 200

        first_line = resp.text.strip().split("\n")[0]
        record = _json.loads(first_line)
        assert record["type"] == "brand_manifest"
        assert record["brand_name"] == brand.name
