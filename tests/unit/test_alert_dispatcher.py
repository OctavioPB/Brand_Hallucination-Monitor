"""Unit tests for AlertDispatcher service."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.services.alert_dispatcher import AlertDispatcher, _alert_payload, _hmac_signature


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_alert(severity: str = "CRITICAL") -> MagicMock:
    alert = MagicMock()
    alert.id = uuid.uuid4()
    alert.organization_id = "org_test"
    alert.brand_id = uuid.uuid4()
    alert.severity = severity
    alert.alert_type = "sps_threshold_breach"
    alert.message = "SPS dropped below threshold"
    alert.created_at = datetime(2026, 5, 14, 10, 0, 0, tzinfo=timezone.utc)
    return alert


def _make_settings(
    slack_url: str = "",
    resend_key: str = "",
    resend_from: str = "noreply@test.io",
    cooldown: int = 60,
) -> MagicMock:
    s = MagicMock()
    s.slack_webhook_url = slack_url
    s.resend_api_key = resend_key
    s.resend_from_email = resend_from
    s.alert_rule_cooldown_minutes = cooldown
    return s


# ---------------------------------------------------------------------------
# _alert_payload
# ---------------------------------------------------------------------------

class TestAlertPayload:
    def test_contains_required_keys(self) -> None:
        alert = _make_alert()
        payload = _alert_payload(alert)
        for key in ("event", "alert_id", "organization_id", "brand_id", "severity", "message"):
            assert key in payload

    def test_event_name(self) -> None:
        assert _alert_payload(_make_alert())["event"] == "hallucin8.alert"

    def test_severity_preserved(self) -> None:
        assert _alert_payload(_make_alert("HIGH"))["severity"] == "HIGH"


# ---------------------------------------------------------------------------
# _hmac_signature
# ---------------------------------------------------------------------------

class TestHmacSignature:
    def test_deterministic(self) -> None:
        payload = b"hello world"
        assert _hmac_signature(payload, "secret") == _hmac_signature(payload, "secret")

    def test_different_secrets_differ(self) -> None:
        payload = b"hello world"
        assert _hmac_signature(payload, "secret1") != _hmac_signature(payload, "secret2")

    def test_hex_string_format(self) -> None:
        sig = _hmac_signature(b"data", "key")
        assert all(c in "0123456789abcdef" for c in sig)


# ---------------------------------------------------------------------------
# _severity_matches
# ---------------------------------------------------------------------------

class TestSeverityMatches:
    def test_match(self) -> None:
        assert AlertDispatcher._severity_matches("CRITICAL", "CRITICAL,HIGH") is True

    def test_no_match(self) -> None:
        assert AlertDispatcher._severity_matches("LOW", "CRITICAL,HIGH") is False

    def test_case_insensitive(self) -> None:
        assert AlertDispatcher._severity_matches("critical", "CRITICAL") is True

    def test_single_severity_filter(self) -> None:
        assert AlertDispatcher._severity_matches("HIGH", "HIGH") is True

    def test_medium_in_all_filter(self) -> None:
        assert AlertDispatcher._severity_matches("MEDIUM", "LOW,MEDIUM,HIGH,CRITICAL") is True


# ---------------------------------------------------------------------------
# _dispatch_slack — no URL configured skips dispatch
# ---------------------------------------------------------------------------

class TestDispatchSlack:
    @pytest.mark.asyncio
    async def test_skips_when_no_slack_url(self) -> None:
        db = AsyncMock()
        settings = _make_settings(slack_url="")
        dispatcher = AlertDispatcher(db, settings)

        alert = _make_alert("CRITICAL")
        # Should return without making any HTTP calls
        with patch("httpx.AsyncClient") as mock_client:
            await dispatcher._dispatch_slack(alert)
            mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_for_low_severity(self) -> None:
        db = AsyncMock()
        settings = _make_settings(slack_url="https://hooks.slack.com/test")
        dispatcher = AlertDispatcher(db, settings)

        alert = _make_alert("LOW")
        with patch("httpx.AsyncClient") as mock_client:
            await dispatcher._dispatch_slack(alert)
            mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_posts_to_slack_on_critical(self) -> None:
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()

        settings = _make_settings(slack_url="https://hooks.slack.com/test123")
        dispatcher = AlertDispatcher(db, settings)
        alert = _make_alert("CRITICAL")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await dispatcher._dispatch_slack(alert)

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert call_kwargs[0][0] == "https://hooks.slack.com/test123"


# ---------------------------------------------------------------------------
# _dispatch_email — skips if no Resend key
# ---------------------------------------------------------------------------

class TestDispatchEmail:
    @pytest.mark.asyncio
    async def test_skips_when_no_resend_key(self) -> None:
        db = AsyncMock()
        settings = _make_settings(resend_key="")
        dispatcher = AlertDispatcher(db, settings)
        alert = _make_alert("CRITICAL")

        with patch("httpx.AsyncClient") as mock_client:
            await dispatcher._dispatch_email(alert)
            mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_for_non_critical(self) -> None:
        db = AsyncMock()
        settings = _make_settings(resend_key="re_key")
        dispatcher = AlertDispatcher(db, settings)
        alert = _make_alert("HIGH")

        with patch("httpx.AsyncClient") as mock_client:
            await dispatcher._dispatch_email(alert)
            mock_client.assert_not_called()
