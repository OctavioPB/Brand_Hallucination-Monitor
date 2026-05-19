"""Onboarding API — self-serve signup, brand wizard, demo seed, NPS, feature flags."""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.api_keys import create_api_key
from apps.api.auth.context import OrgContextDep
from apps.api.database import get_db
from apps.api.models.brand import BrandORM
from apps.api.models.db import AlertORM
from apps.api.models.onboarding import (
    FeatureFlagORM,
    NpsResponseORM,
    OnboardingStateORM,
    OrganizationORM,
)
from apps.api.models.probe_result import ProbeResultORM
from apps.api.models.scan_job import ScanJobORM
from apps.api.models.sps_score import SPSScoreORM
from apps.api.services.onboarding_emails import send_welcome_email

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:64] or "org"


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr
    org_name: str = Field(min_length=1, max_length=128)


class SignupResponse(BaseModel):
    organization_id: str
    org_name: str
    slug: str
    raw_api_key: str
    message: str


class BrandWizardRequest(BaseModel):
    brand_name: str = Field(min_length=1, max_length=128)
    brand_slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    true_attributes: list[str] = Field(default_factory=list, max_length=20)
    false_attributes: list[str] = Field(default_factory=list, max_length=20)
    competitor_names: list[str] = Field(default_factory=list, max_length=10)


class BrandWizardResponse(BaseModel):
    brand_id: str
    brand_name: str
    onboarding_step: str


class OnboardingStateResponse(BaseModel):
    organization_id: str
    current_step: str
    brand_id: str | None
    first_scan_job_id: str | None
    tour_completed_at: datetime | None
    completed_at: datetime | None


class NpsSubmitRequest(BaseModel):
    score: int = Field(ge=0, le=10)
    comment: str | None = Field(default=None, max_length=1000)
    trigger: str = Field(default="first_report")


class FeatureFlagResponse(BaseModel):
    flag_key: str
    enabled: bool
    payload: dict | None = None


# ---------------------------------------------------------------------------
# POST /api/v1/onboarding/signup — unauthenticated, public
# ---------------------------------------------------------------------------

@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    # No auth dependency — public endpoint
)
async def signup(
    payload: SignupRequest,
    background: BackgroundTasks,
    db: DbDep,
) -> SignupResponse:
    """Create org + admin API key in one atomic step."""
    slug_base = _slugify(payload.org_name)

    # Collision-safe slug
    existing = await db.execute(
        select(OrganizationORM).where(OrganizationORM.email == str(payload.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered.")

    slug = slug_base
    counter = 0
    while True:
        clash = await db.execute(
            select(OrganizationORM).where(OrganizationORM.slug == slug)
        )
        if clash.scalar_one_or_none() is None:
            break
        counter += 1
        slug = f"{slug_base}-{counter}"

    org_id = slug  # org_id == slug for human-readable RLS

    org = OrganizationORM(
        name=payload.org_name,
        slug=slug,
        email=str(payload.email),
        plan="trial",
    )
    db.add(org)

    # Onboarding wizard state
    state = OnboardingStateORM(
        organization_id=org_id,
        current_step="account_created",
    )
    db.add(state)

    # Create an admin API key for this org
    api_key_orm, raw_key = await create_api_key(
        db,
        organization_id=org_id,
        name="default-admin",
        role="admin",
    )

    await db.commit()
    await db.refresh(org)

    logger.info("New org signed up", org_id=org_id, email=str(payload.email))
    background.add_task(send_welcome_email, str(payload.email), payload.org_name, raw_key)

    return SignupResponse(
        organization_id=org_id,
        org_name=org.name,
        slug=slug,
        raw_api_key=raw_key,
        message="Welcome to hallucin8. Your API key is shown once — save it securely.",
    )


# ---------------------------------------------------------------------------
# GET /api/v1/onboarding/state
# ---------------------------------------------------------------------------

@router.get("/state", response_model=OnboardingStateResponse)
async def get_onboarding_state(org_ctx: OrgContextDep, db: DbDep) -> OnboardingStateResponse:
    result = await db.execute(
        select(OnboardingStateORM).where(
            OnboardingStateORM.organization_id == org_ctx.organization_id
        )
    )
    state = result.scalar_one_or_none()
    if state is None:
        raise HTTPException(status_code=404, detail="Onboarding state not found.")

    return OnboardingStateResponse(
        organization_id=state.organization_id,
        current_step=state.current_step,
        brand_id=str(state.brand_id) if state.brand_id else None,
        first_scan_job_id=str(state.first_scan_job_id) if state.first_scan_job_id else None,
        tour_completed_at=state.tour_completed_at,
        completed_at=state.completed_at,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/onboarding/brand-wizard — step 2: create brand
# ---------------------------------------------------------------------------

@router.post("/brand-wizard", response_model=BrandWizardResponse, status_code=status.HTTP_201_CREATED)
async def brand_wizard(
    payload: BrandWizardRequest,
    org_ctx: OrgContextDep,
    background: BackgroundTasks,
    db: DbDep,
) -> BrandWizardResponse:
    """Step 2 of onboarding: create the brand + trigger first scan."""
    # Check slug uniqueness
    clash = await db.execute(
        select(BrandORM).where(BrandORM.slug == payload.brand_slug)
    )
    if clash.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Brand slug already taken.")

    brand = BrandORM(
        organization_id=org_ctx.organization_id,
        name=payload.brand_name,
        slug=payload.brand_slug,
        manifest={
            "true_attributes": payload.true_attributes,
            "false_attributes": payload.false_attributes,
            "competitor_list": payload.competitor_names,
            "regulatory_claims_to_avoid": [],
        },
    )
    db.add(brand)
    await db.flush()  # get brand.id

    # Trigger first scan job
    scan_job = ScanJobORM(
        brand_id=brand.id,
        status="pending",
        job_type="llm_probe",
    )
    db.add(scan_job)
    await db.flush()

    # Advance onboarding state
    state_result = await db.execute(
        select(OnboardingStateORM).where(
            OnboardingStateORM.organization_id == org_ctx.organization_id
        )
    )
    state = state_result.scalar_one_or_none()
    if state:
        state.current_step = "scan_triggered"
        state.brand_id = brand.id
        state.first_scan_job_id = scan_job.id

    await db.commit()

    logger.info(
        "Brand wizard completed",
        org_id=org_ctx.organization_id,
        brand_id=str(brand.id),
        scan_job_id=str(scan_job.id),
    )

    return BrandWizardResponse(
        brand_id=str(brand.id),
        brand_name=brand.name,
        onboarding_step="scan_triggered",
    )


# ---------------------------------------------------------------------------
# POST /api/v1/onboarding/tour-complete — mark product tour done
# ---------------------------------------------------------------------------

@router.post("/tour-complete", status_code=status.HTTP_204_NO_CONTENT)
async def tour_complete(org_ctx: OrgContextDep, db: DbDep) -> None:
    result = await db.execute(
        select(OnboardingStateORM).where(
            OnboardingStateORM.organization_id == org_ctx.organization_id
        )
    )
    state = result.scalar_one_or_none()
    if state:
        state.tour_completed_at = datetime.utcnow()
        if state.current_step == "scan_triggered":
            state.current_step = "tour_completed"
        await db.commit()


# ---------------------------------------------------------------------------
# POST /api/v1/onboarding/demo/seed — populate fictional demo brand
# ---------------------------------------------------------------------------

_DEMO_ORG_ID = "demo"

@router.post("/demo/seed", status_code=status.HTTP_201_CREATED)
async def seed_demo_data(db: DbDep, force: bool = False) -> dict[str, str]:
    """Idempotent: seed a fictional 'AcmeCorp' brand for unauthenticated evaluation.

    Pass ?force=true to wipe and re-seed (useful in dev to refresh demo data).
    """
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal

    existing_result = await db.execute(
        select(OrganizationORM).where(OrganizationORM.slug == _DEMO_ORG_ID)
    )
    existing_org = existing_result.scalar_one_or_none()

    if existing_org and not force:
        return {"status": "already_seeded", "org_id": _DEMO_ORG_ID}

    if existing_org and force:
        # Wipe all demo data before re-seeding
        from sqlalchemy import delete
        await db.execute(delete(SPSScoreORM).where(
            SPSScoreORM.brand_id.in_(
                select(BrandORM.id).where(BrandORM.organization_id == _DEMO_ORG_ID)
            )
        ))
        await db.execute(delete(ProbeResultORM).where(ProbeResultORM.organization_id == _DEMO_ORG_ID))
        await db.execute(delete(AlertORM).where(AlertORM.organization_id == _DEMO_ORG_ID))
        await db.execute(delete(BrandORM).where(BrandORM.organization_id == _DEMO_ORG_ID))
        await db.execute(delete(OrganizationORM).where(OrganizationORM.slug == _DEMO_ORG_ID))
        await db.flush()

    demo_org = OrganizationORM(
        name="AcmeCorp (Demo)",
        slug=_DEMO_ORG_ID,
        email="demo@hallucin8.io",
        plan="trial",
        is_demo=True,
        onboarding_completed=True,
    )
    db.add(demo_org)

    demo_brand = BrandORM(
        organization_id=_DEMO_ORG_ID,
        name="AcmeCorp",
        slug="acmecorp-demo",
        manifest={
            "true_attributes": ["reliable", "SOC2-certified", "enterprise-grade", "cloud-native"],
            "false_attributes": ["open-source", "free", "consumer-focused"],
            "competitor_list": ["Acme Rival Inc.", "FastStart SaaS"],
            "regulatory_claims_to_avoid": ["HIPAA-compliant", "FDA-cleared"],
        },
    )
    db.add(demo_brand)
    await db.flush()  # get demo_brand.id

    now = datetime.now(tz=timezone.utc)

    # SPS scores — two weeks of data for 6 intent clusters
    _CLUSTERS = [
        ("reliability",       0.82),
        ("innovation",        0.74),
        ("pricing_value",     0.61),
        ("market_leadership", 0.78),
        ("compliance",        0.91),
        ("support_quality",   0.69),
    ]
    for week_offset in range(2):
        calc_at = now - timedelta(days=7 * week_offset)
        for cluster_slug, base_score in _CLUSTERS:
            drift = 0.03 * week_offset
            db.add(SPSScoreORM(
                brand_id=demo_brand.id,
                intent_cluster_slug=cluster_slug,
                score=round(base_score - drift, 4),
                model_version="text-embedding-3-small",
                dag_run_id=f"demo-run-wk{week_offset}",
                calculated_at=calc_at,
            ))

    # Probe results — hallucination samples across 3 LLMs
    _PROBES = [
        ("gpt-4o",           "Is AcmeCorp open-source software?",
         "AcmeCorp is an enterprise-grade, cloud-native platform. It is not open-source.", 0),
        ("gemini-1.5-pro",   "What is AcmeCorp known for?",
         "AcmeCorp is a free, consumer-focused tool similar to FastStart SaaS.", 2),
        ("claude-3-opus",    "Does AcmeCorp offer HIPAA compliance?",
         "AcmeCorp is SOC2-certified but does not advertise HIPAA compliance.", 1),
        ("gpt-4o",           "How does AcmeCorp compare to its competitors?",
         "AcmeCorp is a reliable, enterprise-grade solution, unlike open-source alternatives.", 0),
    ]
    for i, (model, prompt, response, hallucinations) in enumerate(_PROBES):
        db.add(ProbeResultORM(
            brand_id=demo_brand.id,
            organization_id=_DEMO_ORG_ID,
            model_name=model,
            probe_prompt=prompt,
            llm_response=response,
            tokens_input=80 + i * 12,
            tokens_output=60 + i * 8,
            cost_usd=Decimal("0.0024") + Decimal("0.0003") * i,
            latency_ms=820 + i * 110,
            hallucinations_detected=hallucinations,
            dag_run_id="demo-run-wk0",
            probed_at=now - timedelta(hours=i * 6),
        ))

    # Alerts — three active alerts of varying severity
    _ALERTS = [
        ("HIGH",     "hallucination_detected",
         "GPT-4o described AcmeCorp as 'open-source' in 3 of 10 probes — contradicts brand manifest."),
        ("MEDIUM",   "competitor_confusion",
         "Gemini 1.5 Pro conflated AcmeCorp with FastStart SaaS in 2 of 10 probes."),
        ("LOW",      "sps_decline",
         "SPS score for 'pricing_value' dropped 8 pts week-over-week (0.69 → 0.61)."),
    ]
    for severity, alert_type, message in _ALERTS:
        db.add(AlertORM(
            organization_id=_DEMO_ORG_ID,
            brand_id=demo_brand.id,
            severity=severity,
            alert_type=alert_type,
            message=message,
            acknowledged=False,
        ))

    await db.commit()
    logger.info("Demo data seeded", org_id=_DEMO_ORG_ID)
    return {"status": "seeded", "org_id": _DEMO_ORG_ID, "brand_slug": "acmecorp-demo"}


# ---------------------------------------------------------------------------
# GET /api/v1/onboarding/demo/access — issue a fresh demo API key (no auth)
# ---------------------------------------------------------------------------

@router.get("/demo/access")
async def demo_access(db: DbDep) -> dict[str, str]:
    """Return a fresh API key for the demo org. Public — local dev only."""
    existing = await db.execute(
        select(OrganizationORM).where(OrganizationORM.slug == _DEMO_ORG_ID)
    )
    if not existing.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Demo not seeded. POST /demo/seed first.")
    _, raw_key = await create_api_key(db, organization_id=_DEMO_ORG_ID, name="demo-session", role="admin")
    await db.commit()
    return {"api_key": raw_key, "org_id": _DEMO_ORG_ID}


# ---------------------------------------------------------------------------
# POST /api/v1/onboarding/nps — submit NPS score
# ---------------------------------------------------------------------------

@router.post("/nps", status_code=status.HTTP_204_NO_CONTENT)
async def submit_nps(
    payload: NpsSubmitRequest,
    org_ctx: OrgContextDep,
    db: DbDep,
) -> None:
    nps = NpsResponseORM(
        organization_id=org_ctx.organization_id,
        score=payload.score,
        comment=payload.comment,
        trigger=payload.trigger,
    )
    db.add(nps)
    await db.commit()
    logger.info("NPS submitted", org_id=org_ctx.organization_id, score=payload.score)


# ---------------------------------------------------------------------------
# GET /api/v1/onboarding/flags — feature flags for the caller's org
# ---------------------------------------------------------------------------

@router.get("/flags", response_model=list[FeatureFlagResponse])
async def get_feature_flags(org_ctx: OrgContextDep, db: DbDep) -> list[FeatureFlagResponse]:
    """Return effective flags: org-level overrides take precedence over global defaults."""
    # Global defaults
    global_result = await db.execute(
        select(FeatureFlagORM).where(FeatureFlagORM.organization_id.is_(None))
    )
    globals_by_key: dict[str, FeatureFlagORM] = {
        f.flag_key: f for f in global_result.scalars().all()
    }

    # Org-level overrides
    org_result = await db.execute(
        select(FeatureFlagORM).where(
            FeatureFlagORM.organization_id == org_ctx.organization_id
        )
    )
    org_overrides: dict[str, FeatureFlagORM] = {
        f.flag_key: f for f in org_result.scalars().all()
    }

    merged = {**globals_by_key, **org_overrides}
    return [
        FeatureFlagResponse(
            flag_key=f.flag_key,
            enabled=f.enabled,
            payload=f.payload,
        )
        for f in merged.values()
    ]
