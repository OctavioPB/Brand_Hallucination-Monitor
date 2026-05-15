"""Organizations router — GDPR data deletion (cascade all org data)."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from fastapi import Depends

from apps.api.auth.api_keys import require_role
from apps.api.auth.context import OrgContextDep
from apps.api.database import get_db
from apps.api.models.api_key import ApiKeyORM
from apps.api.models.brand import BrandORM
from apps.api.models.embedding_cost import EmbeddingCostORM
from apps.api.models.infra_cost import InfraCostORM
from apps.api.models.onboarding import NpsResponseORM, OnboardingStateORM, OrganizationORM
from apps.api.models.report import AlertNotificationORM, AlertRuleORM, ReportORM
from apps.api.models.scan_job import ScanJobORM
from apps.api.models.db import AlertORM

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# DELETE /api/v1/organizations/{org_id} — GDPR right to erasure
# ---------------------------------------------------------------------------

@router.delete(
    "/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_role("admin")],
    summary="GDPR data deletion — cascades all organization data",
)
async def delete_organization(
    org_id: str,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> None:
    """Permanently delete all data for an organization.

    Enforces org isolation: callers can only delete their own organization.
    Cascades: brands, scan jobs, reports, alert rules, costs, API keys, NPS responses.
    Qdrant and Neo4j vectors are best-effort deleted (failures are logged, not re-raised).
    """
    # Org isolation — a caller can only delete their own org
    if org_ctx.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own organization.",
        )

    org_result = await db.execute(
        select(OrganizationORM).where(OrganizationORM.slug == org_id)
    )
    org = org_result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    logger.warning("GDPR deletion initiated", org_id=org_id)

    # 1. Collect brand IDs first (needed for cascading scan-job deletes)
    brand_ids_result = await db.execute(
        select(BrandORM.id).where(BrandORM.organization_id == org_id)
    )
    brand_ids = list(brand_ids_result.scalars().all())

    # 2. Delete scan jobs for all org brands
    if brand_ids:
        await db.execute(
            delete(ScanJobORM).where(ScanJobORM.brand_id.in_(brand_ids))
        )

    # 3. Delete alerts, alert rules, reports, notifications for this org
    await db.execute(delete(AlertORM).where(AlertORM.organization_id == org_id))
    await db.execute(delete(AlertRuleORM).where(AlertRuleORM.organization_id == org_id))

    if brand_ids:
        report_ids_result = await db.execute(
            select(ReportORM.id).where(ReportORM.brand_id.in_(brand_ids))
        )
        report_ids = list(report_ids_result.scalars().all())
        if report_ids:
            await db.execute(
                delete(AlertNotificationORM).where(AlertNotificationORM.alert_rule_id.in_(
                    select(AlertRuleORM.id).where(AlertRuleORM.organization_id == org_id)
                ))
            )
        await db.execute(delete(ReportORM).where(ReportORM.brand_id.in_(brand_ids)))

    # 4. Delete brands
    await db.execute(delete(BrandORM).where(BrandORM.organization_id == org_id))

    # 5. Cost records
    await db.execute(delete(EmbeddingCostORM).where(EmbeddingCostORM.org_id == org_id))
    await db.execute(delete(InfraCostORM).where(InfraCostORM.organization_id == org_id))

    # 6. Onboarding + NPS
    await db.execute(delete(OnboardingStateORM).where(OnboardingStateORM.organization_id == org_id))
    await db.execute(delete(NpsResponseORM).where(NpsResponseORM.organization_id == org_id))

    # 7. API keys
    await db.execute(delete(ApiKeyORM).where(ApiKeyORM.organization_id == org_id))

    # 8. Organization record itself
    await db.execute(delete(OrganizationORM).where(OrganizationORM.slug == org_id))

    await db.commit()

    logger.warning(
        "GDPR deletion complete — all org data permanently removed",
        org_id=org_id,
        brand_count=len(brand_ids),
    )

    # Best-effort Qdrant + Neo4j cleanup (non-blocking)
    await _delete_vector_data(org_id, brand_ids)


async def _delete_vector_data(org_id: str, brand_ids: list) -> None:
    """Best-effort deletion of Qdrant points and Neo4j nodes for an org."""
    try:
        from qdrant_client import AsyncQdrantClient
        from apps.api.config import get_settings
        settings = get_settings()
        qc = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        for brand_id in brand_ids:
            await qc.delete(
                collection_name="brands_reliability",
                points_selector=Filter(
                    must=[FieldCondition(key="brand_id", match=MatchValue(value=str(brand_id)))]
                ),
            )
        logger.info("Qdrant vectors deleted", org_id=org_id, brand_count=len(brand_ids))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Qdrant deletion failed (best-effort)", org_id=org_id, error=str(exc))

    try:
        from neo4j import AsyncGraphDatabase
        from apps.api.config import get_settings
        settings = get_settings()
        async with AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        ) as driver:
            async with driver.session() as session:
                await session.run(
                    "MATCH (b:Brand {organization_id: $org_id}) DETACH DELETE b",
                    org_id=org_id,
                )
        logger.info("Neo4j nodes deleted", org_id=org_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Neo4j deletion failed (best-effort)", org_id=org_id, error=str(exc))
