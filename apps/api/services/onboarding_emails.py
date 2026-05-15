"""Onboarding email sequence via Resend — D+0, D+3, D+7."""
from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------

_WELCOME_SUBJECT = "Welcome to hallucin8 — your brand safety dashboard is ready"

_WELCOME_BODY = """\
Hi there,

Welcome to hallucin8. Your workspace is set up and your first API key is ready.

---

GETTING STARTED

1. Add your brand details in the Brand Setup wizard
2. Trigger your first scan to see how AI models perceive your brand
3. Set alert rules to be notified when perception drifts

Your API key (save it securely — shown only once):
{raw_api_key}

Dashboard: {dashboard_url}
API docs:  {api_docs_url}

---

If you have questions, reply to this email or open the chat widget in the dashboard.

The hallucin8 team
"""

_D3_SUBJECT = "3 days in — how is your first scan looking?"

_D3_BODY = """\
Hi,

It's been 3 days since you joined hallucin8. By now, your first brand scan
should be complete and visible in your dashboard.

KEY THINGS TO CHECK

• Semantic Proximity Score (SPS): are the right concepts associated with your brand?
• Hallucination feed: any factual errors the models are telling about you?
• Competitor positioning: where do you rank versus your named competitors?

NEXT STEP: Set up an alert rule so you're notified automatically when
perception shifts. It takes 2 minutes.

Dashboard: {dashboard_url}/alerts

The hallucin8 team
"""

_D7_SUBJECT = "Your brand in AI — first week summary"

_D7_BODY = """\
Hi,

One week with hallucin8. Here's what we recommend doing this week:

1. DOWNLOAD YOUR FIRST REPORT
   Go to Reports → Generate Report. Share it with your team.

2. CONFIGURE WEEKLY DIGESTS
   Set up a Slack webhook to receive automatic summaries.

3. INVITE A COLLEAGUE
   Create an analyst API key under Settings → API Keys.

You're on the Trial plan. If you'd like to discuss upgrading to Beta or Pro,
reply to this email and we'll set up a call.

The hallucin8 team
"""


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------

async def _send_via_resend(
    to: str,
    subject: str,
    text: str,
) -> None:
    """Send a plain-text email via the Resend API."""
    try:
        import httpx
        from apps.api.config import get_settings
        settings = get_settings()

        if not settings.resend_api_key:
            logger.warning("RESEND_API_KEY not set — skipping email", to=to, subject=subject)
            return

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.resend_from_email,
                    "to": [to],
                    "subject": subject,
                    "text": text,
                },
            )
            resp.raise_for_status()
            logger.info("Email sent", to=to, subject=subject, status=resp.status_code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Email delivery failed (fail-open)", to=to, subject=subject, error=str(exc))


async def send_welcome_email(to: str, org_name: str, raw_api_key: str) -> None:
    """D+0: send immediately after signup."""
    from apps.api.config import get_settings
    settings = get_settings()
    dashboard_url = "http://localhost:3000"  # overrideable via env in prod

    body = _WELCOME_BODY.format(
        org_name=org_name,
        raw_api_key=raw_api_key,
        dashboard_url=dashboard_url,
        api_docs_url=f"{settings.api_port and 'http://localhost:8000'}/api/docs",
    )
    await _send_via_resend(to, _WELCOME_SUBJECT, body)


async def send_d3_email(to: str) -> None:
    """D+3: check-in email — triggered by Airflow dag_onboarding_emails."""
    dashboard_url = "http://localhost:3000"
    body = _D3_BODY.format(dashboard_url=dashboard_url)
    await _send_via_resend(to, _D3_SUBJECT, body)


async def send_d7_email(to: str) -> None:
    """D+7: first-week summary email."""
    dashboard_url = "http://localhost:3000"
    body = _D7_BODY.format(dashboard_url=dashboard_url)
    await _send_via_resend(to, _D7_SUBJECT, body)
