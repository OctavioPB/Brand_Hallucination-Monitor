"""Smoke tests: API health endpoint and model imports."""
import pytest


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_api_status_endpoint(client):
    response = await client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "0.1.0"
    assert data["status"] == "operational"


def test_model_imports():
    from apps.api.models import Brand, BrandCreate, BrandManifest, Competitor, ScanJob, ScanJobStatus
    assert ScanJobStatus.PENDING == "pending"
    assert ScanJobStatus.COMPLETED == "completed"


def test_brand_manifest_defaults():
    from apps.api.models import BrandManifest
    m = BrandManifest()
    assert m.true_attributes == []
    assert m.false_attributes == []


def test_brand_create_slug_validation():
    from pydantic import ValidationError
    from apps.api.models import BrandCreate
    with pytest.raises(ValidationError):
        BrandCreate(organization_id="org-1", name="Test", slug="INVALID SLUG!")
