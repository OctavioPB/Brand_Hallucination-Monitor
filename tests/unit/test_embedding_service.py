"""Unit tests for EmbeddingService — no OpenAI API calls, no live Redis."""
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from ml.embeddings.service import EmbeddingService, _sha256


def _make_service(redis_store: dict | None = None) -> tuple[EmbeddingService, dict]:
    """Build EmbeddingService with an InMemory Redis mock and no DB."""
    store: dict = {} if redis_store is None else redis_store

    redis_mock = MagicMock()

    def mock_get(key: str) -> str | None:
        return store.get(key)

    def mock_set(key: str, value: str, ex: int | None = None) -> None:
        store[key] = value

    def mock_incrby(key: str, n: int) -> int:
        store[key] = store.get(key, 0) + n
        return store[key]

    def mock_decrby(key: str, n: int) -> int:
        store[key] = store.get(key, 0) - n
        return store[key]

    redis_mock.get.side_effect = mock_get
    redis_mock.set.side_effect = mock_set
    redis_mock.incrby.side_effect = mock_incrby
    redis_mock.decrby.side_effect = mock_decrby
    redis_mock.expire.return_value = True

    svc = EmbeddingService(api_key="test-key", redis_client=redis_mock, db_url=None)
    return svc, store


def _fake_openai_response(texts: list[str]) -> tuple[list[list[float]], int]:
    """Return deterministic fake vectors proportional to text length."""
    vectors = [[float(len(t) % 10) / 10.0] * 1536 for t in texts]
    tokens = sum(len(t) // 4 + 1 for t in texts)
    return vectors, tokens


class TestHashHelper:
    def test_sha256_is_deterministic(self) -> None:
        assert _sha256("hello") == _sha256("hello")

    def test_sha256_differs_for_different_inputs(self) -> None:
        assert _sha256("hello") != _sha256("world")

    def test_sha256_length(self) -> None:
        assert len(_sha256("any text")) == 64


class TestCacheHitPath:
    def test_all_cached_no_openai_call(self) -> None:
        svc, store = _make_service()
        text = "AcmeCorp is the market leader"
        h = _sha256(text)
        fake_vector = [0.5] * 1536
        store[f"emb:v1:{h}"] = json.dumps(fake_vector)

        with patch.object(svc, "_call_openai") as mock_api:
            result = svc.embed_batch([("id1", text)])
            mock_api.assert_not_called()

        assert h in result
        assert result[h] == fake_vector

    def test_partial_cache_only_calls_api_for_uncached(self) -> None:
        svc, store = _make_service()

        cached_text = "cached text here"
        uncached_text = "this is brand new content"
        h_cached = _sha256(cached_text)
        fake_vector = [0.3] * 1536
        store[f"emb:v1:{h_cached}"] = json.dumps(fake_vector)

        with patch.object(svc, "_call_openai", side_effect=_fake_openai_response) as mock_api:
            result = svc.embed_batch([("a", cached_text), ("b", uncached_text)])
            mock_api.assert_called_once()
            # Only the uncached text was passed to the API
            called_texts = mock_api.call_args[0][0]
            assert called_texts == [uncached_text]

        assert h_cached in result
        assert _sha256(uncached_text) in result


class TestBatchSplitting:
    def test_large_batch_split_into_batches_of_100(self) -> None:
        svc, _ = _make_service()
        n_items = 250
        items = [(str(i), f"text number {i} for brand AcmeCorp") for i in range(n_items)]

        call_count = 0

        def fake_api(texts: list[str]) -> tuple[list[list[float]], int]:
            nonlocal call_count
            call_count += 1
            return _fake_openai_response(texts)

        with patch.object(svc, "_call_openai", side_effect=fake_api):
            result = svc.embed_batch(items)

        # 250 items → ceil(250/100) = 3 API calls
        assert call_count == 3
        assert len(result) == n_items


class TestCacheWrite:
    def test_new_vectors_written_to_cache(self) -> None:
        svc, store = _make_service()
        text = "brand new mention"

        with patch.object(svc, "_call_openai", side_effect=_fake_openai_response):
            svc.embed_batch([("id", text)])

        h = _sha256(text)
        assert f"emb:v1:{h}" in store
        cached_vec = json.loads(store[f"emb:v1:{h}"])
        assert len(cached_vec) == 1536


class TestEmptyInput:
    def test_empty_list_returns_empty_dict(self) -> None:
        svc, _ = _make_service()
        result = svc.embed_batch([])
        assert result == {}


class TestTokenBucket:
    def test_token_bucket_proceeds_under_limit(self) -> None:
        svc, store = _make_service()
        # Set current bucket usage well under limit
        import time
        bucket_key = f"tb:openai:embeddings:{int(time.time()) // 60}"
        store[bucket_key] = 100  # far below 1M

        # Should not block — just calls incrby and returns
        svc._consume_tokens(1000)

    def test_redis_failure_in_token_bucket_is_fail_open(self) -> None:
        redis_mock = MagicMock()
        redis_mock.incrby.side_effect = Exception("Redis down")
        svc = EmbeddingService(api_key="key", redis_client=redis_mock, db_url=None)
        # Should not raise — fail-open behavior
        svc._consume_tokens(500)


class TestDeduplication:
    def test_duplicate_texts_embedded_once(self) -> None:
        svc, _ = _make_service()
        text = "identical text for two IDs"
        items = [("id1", text), ("id2", text)]  # same text, different IDs

        api_calls: list[list[str]] = []

        def fake_api(texts: list[str]) -> tuple[list[list[float]], int]:
            api_calls.append(texts)
            return _fake_openai_response(texts)

        with patch.object(svc, "_call_openai", side_effect=fake_api):
            result = svc.embed_batch(items)

        # Only one hash exists for the same text
        assert len(result) == 1
        # API called at most once for this text (may be zero if already cached)
        total_texts_sent = sum(len(batch) for batch in api_calls)
        assert total_texts_sent <= 1
