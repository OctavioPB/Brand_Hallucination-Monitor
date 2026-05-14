"""Unit tests for API key generation, hashing, and require_role guard."""
from __future__ import annotations

import hashlib
import uuid

import pytest

from apps.api.auth.api_keys import generate_api_key


class TestGenerateApiKey:
    def test_returns_tuple_of_raw_and_hash(self) -> None:
        raw, key_hash = generate_api_key()
        assert isinstance(raw, str)
        assert isinstance(key_hash, str)

    def test_raw_key_has_hk_prefix(self) -> None:
        raw, _ = generate_api_key()
        assert raw.startswith("hk_")

    def test_hash_is_sha256_hex(self) -> None:
        raw, key_hash = generate_api_key()
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert key_hash == expected
        assert len(key_hash) == 64

    def test_each_call_produces_unique_key(self) -> None:
        raw1, _ = generate_api_key()
        raw2, _ = generate_api_key()
        assert raw1 != raw2

    def test_hash_uniqueness_follows_raw(self) -> None:
        _, h1 = generate_api_key()
        _, h2 = generate_api_key()
        assert h1 != h2

    def test_raw_key_minimum_length(self) -> None:
        raw, _ = generate_api_key()
        # "hk_" + 32 bytes base64url ≈ 46 chars minimum
        assert len(raw) >= 40


class TestRequireRole:
    def test_require_role_returns_depends(self) -> None:
        from fastapi import params
        from apps.api.auth.api_keys import require_role

        dep = require_role("admin")
        assert isinstance(dep, params.Depends)

    def test_require_role_allows_matching_role(self) -> None:
        """The inner _check function should NOT raise when role matches."""
        import asyncio
        from apps.api.auth.api_keys import require_role
        from apps.api.auth.context import OrgContext

        dep = require_role("admin", "analyst")
        check_fn = dep.dependency

        ctx = OrgContext(organization_id="org-1", user_id="u1", role="admin")

        # Call _check directly — OrgContextDep is a type alias, not a real DI param
        # when called outside of a FastAPI request cycle.
        async def run():
            await check_fn(org_ctx=ctx)  # should not raise

        asyncio.run(run())

    def test_require_role_rejects_wrong_role(self) -> None:
        import asyncio
        from fastapi import HTTPException
        from apps.api.auth.api_keys import require_role
        from apps.api.auth.context import OrgContext

        dep = require_role("admin")
        check_fn = dep.dependency

        ctx = OrgContext(organization_id="org-1", user_id="u1", role="viewer")

        async def run():
            with pytest.raises(HTTPException) as exc_info:
                await check_fn(org_ctx=ctx)
            assert exc_info.value.status_code == 403

        asyncio.run(run())


class TestApiKeyHashing:
    def test_hash_is_deterministic(self) -> None:
        raw = "hk_my-known-key"
        h1 = hashlib.sha256(raw.encode()).hexdigest()
        h2 = hashlib.sha256(raw.encode()).hexdigest()
        assert h1 == h2

    def test_different_keys_different_hashes(self) -> None:
        h1 = hashlib.sha256(b"hk_key1").hexdigest()
        h2 = hashlib.sha256(b"hk_key2").hexdigest()
        assert h1 != h2
