"""Reddit Producer — monitors subreddits for brand mentions via Reddit JSON API.

Uses PRAW (Python Reddit API Wrapper) when OAuth2 credentials are present,
falls back to the public JSON API (unauthenticated, 60 req/min limit).

Rate limiting is enforced by PRAW internally. Without credentials, we apply
a conservative 2-second delay between requests via tenacity.

Reddit ToS: only public posts/comments are read. No private content.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

from apps.workers.kafka.schemas import SourceType
from apps.workers.producers.base import BaseProducer, ProducerConfig

logger = structlog.get_logger(__name__)


@dataclass
class RedditProducerConfig(ProducerConfig):
    subreddits: list[str] = field(default_factory=list)
    # PRAW OAuth2 credentials (optional — falls back to public JSON API)
    client_id: str = ""
    client_secret: str = ""
    user_agent: str = "hallucin8-brand-monitor/1.0"
    # How many recent posts/comments to fetch per subreddit per run
    limit: int = 100
    # Minimum score (upvotes) to include — reduces noise
    min_score: int = 0


class RedditProducer(BaseProducer):
    """Fetches posts and comments mentioning the brand from configured subreddits."""

    source_type = SourceType.REDDIT

    def __init__(self, config: RedditProducerConfig, **kwargs: object) -> None:  # type: ignore[override]
        super().__init__(config, **kwargs)  # type: ignore[arg-type]
        self._reddit_config: RedditProducerConfig = config
        self._reddit = self._build_reddit_client()

    def _build_reddit_client(self) -> object | None:
        cfg = self._reddit_config
        if not (cfg.client_id and cfg.client_secret):
            logger.info("Reddit credentials not configured — using public JSON API")
            return None
        try:
            import praw
            return praw.Reddit(
                client_id=cfg.client_id,
                client_secret=cfg.client_secret,
                user_agent=cfg.user_agent,
                check_for_async=False,
            )
        except ImportError:
            logger.warning("praw not installed — falling back to public JSON API")
            return None

    def fetch_events(self) -> None:
        for subreddit in self._reddit_config.subreddits:
            if self._reddit is not None:
                self._fetch_via_praw(subreddit)
            else:
                self._fetch_via_public_api(subreddit)

    def _fetch_via_praw(self, subreddit_name: str) -> None:
        import praw
        reddit = self._reddit  # type: ignore[union-attr]
        log = logger.bind(subreddit=subreddit_name, brand=self.config.brand_name)
        try:
            subreddit = reddit.subreddit(subreddit_name)
            query = self.config.brand_name
            for submission in subreddit.search(
                query, limit=self._reddit_config.limit, sort="new"
            ):
                if submission.score < self._reddit_config.min_score:
                    continue
                raw_text = f"{submission.title}\n{submission.selftext}".strip()
                if not raw_text:
                    continue
                event = self.make_event(
                    raw_text=raw_text,
                    title=submission.title,
                    source_url=f"https://reddit.com{submission.permalink}",
                    source_id=submission.id,
                    published_at=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
                )
                self.emit(event)
        except Exception as exc:
            log.error("PRAW fetch failed", error=str(exc))

    def _fetch_via_public_api(self, subreddit_name: str) -> None:
        """Unauthenticated Reddit JSON API — limited to 60 req/min."""
        import httpx

        log = logger.bind(subreddit=subreddit_name, brand=self.config.brand_name)
        url = (
            f"https://www.reddit.com/r/{subreddit_name}/search.json"
            f"?q={self.config.brand_name}&sort=new&limit={self._reddit_config.limit}&restrict_sr=1"
        )
        try:
            response = httpx.get(
                url,
                headers={"User-Agent": self._reddit_config.user_agent},
                timeout=15.0,
                follow_redirects=True,
            )
            response.raise_for_status()
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                p = post.get("data", {})
                if p.get("score", 0) < self._reddit_config.min_score:
                    continue
                title = p.get("title", "")
                body = p.get("selftext", "")
                raw_text = f"{title}\n{body}".strip()
                if not raw_text:
                    continue
                created = p.get("created_utc")
                published_at = datetime.fromtimestamp(created, tz=timezone.utc) if created else None
                event = self.make_event(
                    raw_text=raw_text,
                    title=title or None,
                    source_url=f"https://reddit.com{p.get('permalink', '')}",
                    source_id=p.get("id"),
                    published_at=published_at,
                )
                self.emit(event)
            time.sleep(2)  # polite delay for unauthenticated API
        except Exception as exc:
            log.error("Public Reddit API fetch failed", error=str(exc))
