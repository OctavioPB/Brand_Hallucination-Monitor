"""Unit tests for JWT creation and validation.

Tests do not require Redis or PostgreSQL.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

# Guard: skip if PyJWT not installed (Docker-only environment)
pyjwt = pytest.importorskip("jwt", reason="PyJWT not installed")

from apps.api.auth.jwt import create_token, decode_jwt
from apps.api.config import get_settings
from fastapi import HTTPException


class TestCreateToken:
    def test_creates_valid_token(self) -> None:
        token = create_token(organization_id="org-123", role="admin")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_payload_fields(self) -> None:
        token = create_token(organization_id="org-456", user_id="user-1", role="analyst")
        payload = decode_jwt(token)
        assert payload["organization_id"] == "org-456"
        assert payload["sub"] == "user-1"
        assert payload["role"] == "analyst"

    def test_default_role_is_admin(self) -> None:
        token = create_token(organization_id="org-x")
        payload = decode_jwt(token)
        assert payload["role"] == "admin"


class TestDecodeJwt:
    def test_valid_token_decodes(self) -> None:
        token = create_token(organization_id="org-test")
        payload = decode_jwt(token)
        assert payload["organization_id"] == "org-test"

    def test_expired_token_raises_401(self) -> None:
        token = create_token(
            organization_id="org-test",
            expires_in=timedelta(seconds=-1),  # already expired
        )
        with pytest.raises(HTTPException) as exc_info:
            decode_jwt(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_invalid_token_raises_401(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            decode_jwt("not.a.valid.jwt")
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self) -> None:
        token = create_token(organization_id="org-test")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException) as exc_info:
            decode_jwt(tampered)
        assert exc_info.value.status_code == 401

    def test_supabase_app_metadata_format(self) -> None:
        """JWT with app_metadata nesting (Supabase format) is decoded correctly."""
        import jwt as pyjwt
        from datetime import datetime, timezone

        settings = get_settings()
        payload = {
            "sub": "supabase-user-id",
            "app_metadata": {"organization_id": "org-supabase", "role": "viewer"},
            "iat": datetime.now(tz=timezone.utc),
            "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        decoded = decode_jwt(token)
        assert decoded["app_metadata"]["organization_id"] == "org-supabase"


class TestOrgContextFromJwt:
    """Test that _auth_via_jwt extracts OrgContext correctly."""

    def test_flat_payload(self) -> None:
        from apps.api.auth.context import _auth_via_jwt

        token = create_token(organization_id="org-flat", role="analyst")
        ctx = _auth_via_jwt(token)
        assert ctx.organization_id == "org-flat"
        assert ctx.role == "analyst"

    def test_app_metadata_payload(self) -> None:
        import jwt as pyjwt
        from datetime import datetime, timezone
        from apps.api.auth.context import _auth_via_jwt

        settings = get_settings()
        payload = {
            "sub": "user-x",
            "app_metadata": {"organization_id": "org-meta", "role": "viewer"},
            "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        ctx = _auth_via_jwt(token)
        assert ctx.organization_id == "org-meta"
        assert ctx.role == "viewer"

    def test_missing_organization_id_raises_401(self) -> None:
        import jwt as pyjwt
        from datetime import datetime, timezone
        from apps.api.auth.context import _auth_via_jwt

        settings = get_settings()
        payload = {
            "sub": "user-x",
            # no organization_id
            "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1),
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        with pytest.raises(HTTPException) as exc_info:
            _auth_via_jwt(token)
        assert exc_info.value.status_code == 401
