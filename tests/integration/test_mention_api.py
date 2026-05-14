"""Integration tests: POST /api/v1/mentions endpoint.

The Kafka producer is mocked — these tests verify the API contract
(request validation, response shape, error handling) without requiring
a live Redpanda instance.
"""
import pytest
from unittest.mock import patch

from apps.workers.kafka.schemas import SourceType


class TestMentionCreateEndpoint:
    @pytest.mark.asyncio
    async def test_valid_mention_returns_202(self, client):
        with patch("apps.api.routers.mentions._publish_sync"):
            response = await client.post(
                "/api/v1/mentions",
                json={
                    "brand_name": "AcmeCorp",
                    "raw_text": "AcmeCorp just released a new feature that everyone loves",
                    "source_type": "manual",
                },
            )
        assert response.status_code == 202
        body = response.json()
        assert body["brand_name"] == "AcmeCorp"
        assert body["status"] == "queued"
        assert len(body["event_id"]) == 36
        assert len(body["content_hash"]) == 64  # SHA-256 hex

    @pytest.mark.asyncio
    async def test_empty_brand_name_rejected(self, client):
        with patch("apps.api.routers.mentions._publish_sync"):
            response = await client.post(
                "/api/v1/mentions",
                json={"brand_name": "", "raw_text": "some text", "source_type": "manual"},
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_raw_text_rejected(self, client):
        with patch("apps.api.routers.mentions._publish_sync"):
            response = await client.post(
                "/api/v1/mentions",
                json={"brand_name": "AcmeCorp", "raw_text": "", "source_type": "manual"},
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_source_type_rss_accepted(self, client):
        with patch("apps.api.routers.mentions._publish_sync"):
            response = await client.post(
                "/api/v1/mentions",
                json={
                    "brand_name": "AcmeCorp",
                    "raw_text": "RSS article about AcmeCorp",
                    "source_type": "rss",
                    "source_url": "https://example.com/article",
                },
            )
        assert response.status_code == 202
        assert response.json()["source_type"] == "rss"

    @pytest.mark.asyncio
    async def test_kafka_unavailable_returns_503(self, client):
        with patch(
            "apps.api.routers.mentions._publish_sync",
            side_effect=Exception("Connection refused"),
        ):
            response = await client.post(
                "/api/v1/mentions",
                json={"brand_name": "AcmeCorp", "raw_text": "test mention", "source_type": "manual"},
            )
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_invalid_source_type_rejected(self, client):
        with patch("apps.api.routers.mentions._publish_sync"):
            response = await client.post(
                "/api/v1/mentions",
                json={
                    "brand_name": "AcmeCorp",
                    "raw_text": "some text",
                    "source_type": "twitter_dm",  # not in enum
                },
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_content_hash_deterministic(self, client):
        """Same raw_text must always produce the same content_hash."""
        with patch("apps.api.routers.mentions._publish_sync"):
            r1 = await client.post(
                "/api/v1/mentions",
                json={"brand_name": "X", "raw_text": "constant text", "source_type": "manual"},
            )
            r2 = await client.post(
                "/api/v1/mentions",
                json={"brand_name": "X", "raw_text": "constant text", "source_type": "manual"},
            )
        assert r1.json()["content_hash"] == r2.json()["content_hash"]
