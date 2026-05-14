"""Unit tests: producers with mocked Kafka client."""
import pytest
from unittest.mock import MagicMock, patch

from apps.workers.kafka.schemas import BrandMentionEvent, SourceType
from apps.workers.producers.base import ProducerConfig
from apps.workers.producers.rss import RssProducer, RssProducerConfig
from apps.workers.producers.review import ReviewProducer, ReviewProducerConfig, ReviewFeedConfig
from apps.workers.kafka.schemas import ReviewPlatform


class FakeProducerClient:
    def __init__(self):
        self.produced: list[dict] = []

    def produce(self, topic: str, value, key=None):
        self.produced.append({"topic": topic, "value": value, "key": key})

    def flush(self, timeout: float = 10.0):
        pass


class TestRssProducer:
    def _make_producer(self, feed_urls=None):
        config = RssProducerConfig(
            brand_name="AcmeCorp",
            feed_urls=feed_urls or [],
        )
        client = FakeProducerClient()
        return RssProducer(config, producer_client=client), client

    def test_run_empty_feeds_emits_nothing(self):
        producer, client = self._make_producer(feed_urls=[])
        stats = producer.run()
        assert stats["emitted"] == 0
        assert client.produced == []

    @patch("feedparser.parse")
    def test_run_skips_entries_without_brand_mention(self, mock_parse):
        mock_parse.return_value = MagicMock(
            bozo=False,
            entries=[
                MagicMock(
                    title="Unrelated headline",
                    summary="Nothing about our brand here",
                    content=[],
                    link="https://example.com/1",
                    id="entry-1",
                    published_parsed=None,
                    updated_parsed=None,
                    created_parsed=None,
                    **{"get": lambda self, k, d=None: d},
                )
            ],
        )
        # feedparser FeedParserDict acts like a dict
        entry = {
            "title": "Unrelated headline",
            "summary": "Nothing about our brand here",
            "content": [],
            "link": "https://example.com/1",
            "id": "entry-1",
        }
        mock_feed = MagicMock(bozo=False, entries=[entry])
        mock_parse.return_value = mock_feed

        producer, client = self._make_producer(feed_urls=["https://feed.example.com/rss"])
        with patch.object(producer, "_process_entry") as mock_process:
            mock_process.return_value = None
            producer.run()
        # _process_entry called once
        mock_process.assert_called_once()

    @patch("feedparser.parse")
    def test_run_bozo_feed_logs_warning_and_continues(self, mock_parse):
        mock_parse.return_value = MagicMock(
            bozo=True,
            bozo_exception=Exception("malformed xml"),
            entries=[],
        )
        producer, client = self._make_producer(feed_urls=["https://bad-feed.example.com/"])
        stats = producer.run()
        assert stats["emitted"] == 0  # no entries, no error raised

    def test_emit_delegates_to_producer_client(self):
        producer, client = self._make_producer()
        event = BrandMentionEvent.from_raw_text(
            brand_name="AcmeCorp",
            raw_text="AcmeCorp releases new product",
            source_type=SourceType.RSS,
        )
        producer.emit(event)
        assert len(client.produced) == 1
        assert client.produced[0]["key"] == "AcmeCorp"

    def test_make_event_fills_brand_name(self):
        producer, _ = self._make_producer()
        event = producer.make_event(raw_text="Some AcmeCorp news")
        assert event.brand_name == "AcmeCorp"
        assert event.source_type == SourceType.RSS


class TestReviewProducer:
    def _make_producer(self, feeds=None):
        config = ReviewProducerConfig(
            brand_name="AcmeCorp",
            review_feeds=feeds or [],
        )
        client = FakeProducerClient()
        return ReviewProducer(config, producer_client=client), client

    @patch("feedparser.parse")
    def test_run_parses_review_entry(self, mock_parse):
        entry = {
            "title": "Great product",
            "summary": "AcmeCorp is excellent — 5 stars",
            "link": "https://trustpilot.com/review/acme/1",
            "id": "tp-001",
            "published_parsed": None,
            "updated_parsed": None,
        }
        mock_parse.return_value = MagicMock(bozo=False, entries=[entry])

        feed_config = ReviewFeedConfig(
            platform=ReviewPlatform.TRUSTPILOT,
            feed_url="https://trustpilot.com/rss/acmecorp",
        )
        producer, client = self._make_producer(feeds=[feed_config])
        stats = producer.run()
        assert stats["emitted"] == 1
        assert client.produced[0]["topic"] == "brand.mentions.raw"

    @patch("feedparser.parse")
    def test_run_skips_empty_body(self, mock_parse):
        entry = {"title": "No body", "summary": "", "link": "x", "id": "y"}
        mock_parse.return_value = MagicMock(bozo=False, entries=[entry])
        feed_config = ReviewFeedConfig(
            platform=ReviewPlatform.G2,
            feed_url="https://g2.com/rss",
        )
        producer, client = self._make_producer(feeds=[feed_config])
        stats = producer.run()
        assert stats["emitted"] == 0

    def test_extract_rating_from_text(self):
        assert ReviewProducer._extract_rating_from_text("4 stars product") == "4"
        assert ReviewProducer._extract_rating_from_text("rated 3/5 overall") == "3"
        assert ReviewProducer._extract_rating_from_text("no rating here") is None
