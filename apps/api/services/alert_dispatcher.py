"""Alert dispatch service — delivers alerts to webhook, Slack, and email channels.

Dispatching is fail-open: a delivery failure is logged and recorded but does NOT
raise an exception that would block the alert creation flow.

Usage:
    dispatcher = AlertDispatcher(db_session, settings)
    await dispatcher.dispatch(alert)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import Settings
from apps.api.models.db import AlertORM
from apps.api.models.report import AlertNotificationORM
from apps.api.models.webhook import WebhookEndpointORM

logger = structlog.get_logger(__name__)

_TIMEOUT = httpx.Timeout(10.0)


def _alert_payload(alert: AlertORM) -> dict[str, Any]:
    return {
        "event": "hallucin8.alert",
        "alert_id": str(alert.id),
        "organization_id": alert.organization_id,
        "brand_id": str(alert.brand_id),
        "severity": alert.severity,
        "alert_type": alert.alert_type,
        "message": alert.message,
        "created_at": alert.created_at.isoformat(),
    }


def _hmac_signature(payload_bytes: bytes, secret: str) -> str:
    """HMAC-SHA256 signature for webhook authenticity verification."""
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


class AlertDispatcher:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self._db = db
        self._settings = settings

    async def dispatch(self, alert: AlertORM) -> None:
        """Fan out the alert to all active matching delivery channels."""
        await self._dispatch_webhooks(alert)
        await self._dispatch_slack(alert)
        await self._dispatch_email(alert)

    # ------------------------------------------------------------------
    # Webhook delivery
    # ------------------------------------------------------------------

    async def _dispatch_webhooks(self, alert: AlertORM) -> None:
        result = await self._db.execute(
            select(WebhookEndpointORM).where(
                WebhookEndpointORM.organization_id == alert.organization_id,
                WebhookEndpointORM.is_active.is_(True),
            )
        )
        webhooks = result.scalars().all()

        for wh in webhooks:
            if not self._severity_matches(alert.severity, wh.severity_filter):
                continue
            await self._post_webhook(alert, wh)

    async def _post_webhook(self, alert: AlertORM, wh: WebhookEndpointORM) -> None:
        notification = AlertNotificationORM(
            id=uuid.uuid4(),
            alert_id=alert.id,
            channel="webhook",
            recipient=wh.url,
            status="pending",
        )
        self._db.add(notification)

        payload_bytes = json.dumps(_alert_payload(alert)).encode()
        headers = {"Content-Type": "application/json"}
        if wh.secret_hash:
            headers["X-Hallucin8-Signature"] = _hmac_signature(payload_bytes, wh.secret_hash)

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(wh.url, content=payload_bytes, headers=headers)
                resp.raise_for_status()

            notification.status = "sent"
            notification.sent_at = datetime.now(tz=timezone.utc)
            logger.info("Webhook delivered", webhook_id=str(wh.id), alert_id=str(alert.id))
        except Exception as exc:
            notification.status = "failed"
            notification.error_message = str(exc)[:1024]
            logger.warning(
                "Webhook delivery failed",
                webhook_id=str(wh.id),
                alert_id=str(alert.id),
                error=str(exc),
            )
        finally:
            await self._db.commit()

    # ------------------------------------------------------------------
    # Slack delivery
    # ------------------------------------------------------------------

    async def _dispatch_slack(self, alert: AlertORM) -> None:
        """Send to the org-level Slack webhook if CRITICAL or HIGH."""
        url = self._settings.slack_webhook_url
        if not url or alert.severity not in ("CRITICAL", "HIGH"):
            return

        severity_emoji = {"CRITICAL": "🚨", "HIGH": "⚠️"}.get(alert.severity, "ℹ️")
        slack_body = {
            "text": f"{severity_emoji} *hallucin8 Alert* — {alert.severity}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"{severity_emoji} *{alert.severity}* · `{alert.alert_type}`\n"
                            f"{alert.message}"
                        ),
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": (
                                f"Brand: `{alert.brand_id}` · "
                                f"Org: `{alert.organization_id}` · "
                                f"{alert.created_at.strftime('%Y-%m-%d %H:%M UTC')}"
                            ),
                        }
                    ],
                },
            ],
        }

        notification = AlertNotificationORM(
            id=uuid.uuid4(),
            alert_id=alert.id,
            channel="slack",
            recipient=url,
            status="pending",
        )
        self._db.add(notification)

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(url, json=slack_body)
                resp.raise_for_status()

            notification.status = "sent"
            notification.sent_at = datetime.now(tz=timezone.utc)
            logger.info("Slack alert delivered", alert_id=str(alert.id))
        except Exception as exc:
            notification.status = "failed"
            notification.error_message = str(exc)[:1024]
            logger.warning("Slack delivery failed", alert_id=str(alert.id), error=str(exc))
        finally:
            await self._db.commit()

    # ------------------------------------------------------------------
    # Email delivery via Resend API
    # ------------------------------------------------------------------

    async def _dispatch_email(self, alert: AlertORM) -> None:
        """Send instant email for CRITICAL alerts if Resend is configured."""
        api_key = self._settings.resend_api_key
        if not api_key or alert.severity != "CRITICAL":
            return

        # For instant email alerts, send to the org's configured recipients.
        # The `emailed_to` field on webhook endpoints holds per-org email addresses.
        result = await self._db.execute(
            select(WebhookEndpointORM).where(
                WebhookEndpointORM.organization_id == alert.organization_id,
                WebhookEndpointORM.is_active.is_(True),
                # Slack webhooks don't have email-like URLs; skip those
            )
        )
        webhooks = result.scalars().all()
        # Collect any email recipients stored in webhook name field when URL is mailto:
        email_recipients = [
            wh.url[7:]
            for wh in webhooks
            if wh.url.startswith("mailto:") and self._severity_matches(alert.severity, wh.severity_filter)
        ]

        if not email_recipients:
            return

        subject = f"[hallucin8 CRITICAL] {alert.alert_type} — {alert.message[:60]}"
        html_body = (
            f"<h2 style='color:#E03448'>⚠ CRITICAL Brand Safety Alert</h2>"
            f"<p><strong>Type:</strong> {alert.alert_type}</p>"
            f"<p><strong>Message:</strong> {alert.message}</p>"
            f"<p><strong>Brand ID:</strong> {alert.brand_id}</p>"
            f"<p><strong>Detected:</strong> {alert.created_at.strftime('%Y-%m-%d %H:%M UTC')}</p>"
            f"<hr/><p style='color:#6B7280;font-size:11px'>"
            f"hallucin8 — SGE Semantic Dominance &amp; Brand Hallucination Monitor</p>"
        )

        for recipient in email_recipients:
            notification = AlertNotificationORM(
                id=uuid.uuid4(),
                alert_id=alert.id,
                channel="email",
                recipient=recipient,
                status="pending",
            )
            self._db.add(notification)

            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    resp = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "from": self._settings.resend_from_email,
                            "to": [recipient],
                            "subject": subject,
                            "html": html_body,
                        },
                    )
                    resp.raise_for_status()

                notification.status = "sent"
                notification.sent_at = datetime.now(tz=timezone.utc)
                logger.info("Email alert delivered", recipient=recipient, alert_id=str(alert.id))
            except Exception as exc:
                notification.status = "failed"
                notification.error_message = str(exc)[:1024]
                logger.warning(
                    "Email delivery failed",
                    recipient=recipient,
                    alert_id=str(alert.id),
                    error=str(exc),
                )

        await self._db.commit()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _severity_matches(alert_severity: str, filter_str: str) -> bool:
        """True if alert_severity is in the comma-separated filter."""
        allowed = {s.strip().upper() for s in filter_str.split(",")}
        return alert_severity.upper() in allowed
