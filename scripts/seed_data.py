"""Seed initial data: intent clusters and sample brands."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from apps.api.database import engine
from apps.api.models.db import Base, BrandORM, IntentClusterORM
from sqlalchemy.ext.asyncio import AsyncSession


INTENT_CLUSTERS = [
    "reliability",
    "innovation",
    "pricing_value",
    "market_leadership",
    "compliance",
    "support_quality",
]

SAMPLE_BRANDS = [
    {"name": "AcmeCorp", "slug": "acmecorp", "organization_id": "seed-org-001"},
    {"name": "BetaSaaS", "slug": "betasaas", "organization_id": "seed-org-001"},
]


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        for cluster_name in INTENT_CLUSTERS:
            cluster = IntentClusterORM(slug=cluster_name, display_name=cluster_name.replace("_", " ").title())
            session.add(cluster)

        for brand_data in SAMPLE_BRANDS:
            brand = BrandORM(**brand_data)
            session.add(brand)

        await session.commit()
        print(f"✓ Seeded {len(INTENT_CLUSTERS)} intent clusters and {len(SAMPLE_BRANDS)} sample brands.")


if __name__ == "__main__":
    asyncio.run(seed())
