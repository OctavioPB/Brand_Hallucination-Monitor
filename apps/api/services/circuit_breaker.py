"""Circuit breaker pattern for external API calls.

Uses Redis to share circuit state across multiple API workers / Celery workers
so that an OpenAI outage trips the breaker globally, not per-process.

States:
  CLOSED    — normal operation; calls pass through
  OPEN      — too many failures; all calls fail fast with CircuitOpenError
  HALF_OPEN — cooldown expired; one probe call allowed through

Tenacity is used for per-call retry with exponential backoff. The circuit
breaker sits above that: if a call still fails after retries, it counts as
a circuit failure.

Usage:
    breaker = CircuitBreaker(redis_client, "openai-embeddings")

    @breaker.call
    def make_api_request():
        return openai_client.embeddings.create(...)

    # Or directly:
    result = breaker.call(make_api_request)
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tenacity import AsyncRetrying

logger = logging.getLogger(__name__)

_CLOSED = "CLOSED"
_OPEN = "OPEN"
_HALF_OPEN = "HALF_OPEN"

T = TypeVar("T")


class CircuitOpenError(Exception):
    """Raised when a call is blocked by an open circuit breaker."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Circuit breaker '{name}' is OPEN — calls blocked")
        self.name = name


class CircuitBreaker:
    """Redis-backed circuit breaker with tenacity retry.

    Args:
        redis_client:       A redis.Redis or redis.asyncio.Redis instance (or None
                            to disable shared state and use in-process counters only).
        name:               Unique name for this breaker (used as Redis key prefix).
        failure_threshold:  Number of failures within the window to trip OPEN.
        recovery_timeout:   Seconds to stay OPEN before moving to HALF_OPEN.
        window_seconds:     Sliding window for failure counting.
        max_retries:        Per-call retry attempts before counting as a failure.
        retry_min_wait:     Minimum seconds between retries (exponential backoff base).
        retry_max_wait:     Maximum seconds between retries.
    """

    def __init__(
        self,
        redis_client: Any,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        window_seconds: int = 120,
        max_retries: int = 3,
        retry_min_wait: float = 1.0,
        retry_max_wait: float = 30.0,
    ) -> None:
        self._redis = redis_client
        self._name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._window_seconds = window_seconds
        self._max_retries = max_retries
        self._retry_min_wait = retry_min_wait
        self._retry_max_wait = retry_max_wait

        # In-process fallback when Redis is unavailable
        self._local_failures = 0
        self._local_state = _CLOSED
        self._local_open_at: float | None = None

    # ------------------------------------------------------------------
    # Keys
    # ------------------------------------------------------------------

    @property
    def _state_key(self) -> str:
        return f"cb:{self._name}:state"

    @property
    def _failures_key(self) -> str:
        return f"cb:{self._name}:failures"

    @property
    def _open_at_key(self) -> str:
        return f"cb:{self._name}:open_at"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def call(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute fn with retry + circuit breaker protection.

        Raises:
            CircuitOpenError: if the breaker is OPEN and blocking calls.
            Exception:        if all retries fail (re-raised from fn).
        """
        state = self._get_state()

        if state == _OPEN:
            # Check if recovery timeout elapsed → transition to HALF_OPEN
            open_at = self._get_open_at()
            if open_at and (time.time() - open_at) >= self._recovery_timeout:
                self._set_state(_HALF_OPEN)
                logger.info("Circuit breaker HALF_OPEN", name=self._name)
            else:
                raise CircuitOpenError(self._name)

        # Execute with tenacity retry
        @retry(
            retry=retry_if_exception_type(Exception),
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(
                min=self._retry_min_wait,
                max=self._retry_max_wait,
            ),
            reraise=True,
        )
        def _with_retry() -> T:
            return fn(*args, **kwargs)

        try:
            result = _with_retry()
            self._on_success()
            return result
        except RetryError as exc:
            self._on_failure()
            raise exc.last_attempt.exception()  # type: ignore[union-attr]
        except Exception:
            self._on_failure()
            raise

    async def async_call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Async version of call() for use with async functions.

        The circuit state is still stored in Redis synchronously (fast, non-blocking).
        Tenacity's AsyncRetrying handles async retry without blocking the event loop.
        """
        state = self._get_state()

        if state == _OPEN:
            open_at = self._get_open_at()
            if open_at and (time.time() - open_at) >= self._recovery_timeout:
                self._set_state(_HALF_OPEN)
                logger.info("Circuit breaker HALF_OPEN", name=self._name)
            else:
                raise CircuitOpenError(self._name)

        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception_type(Exception),
                stop=stop_after_attempt(self._max_retries),
                wait=wait_exponential(min=self._retry_min_wait, max=self._retry_max_wait),
                reraise=True,
            ):
                with attempt:
                    result = await fn(*args, **kwargs)
            self._on_success()
            return result
        except RetryError as exc:
            self._on_failure()
            raise exc.last_attempt.exception()  # type: ignore[union-attr]
        except Exception:
            self._on_failure()
            raise

    def reset(self) -> None:
        """Manually reset to CLOSED (useful after a deployment/fix)."""
        self._set_state(_CLOSED)
        self._set_failures(0)
        logger.info("Circuit breaker manually RESET to CLOSED", name=self._name)

    def status(self) -> dict[str, object]:
        """Return current state summary for health endpoints."""
        state = self._get_state()
        failures = self._get_failures()
        open_at = self._get_open_at()
        return {
            "name": self._name,
            "state": state,
            "failures": failures,
            "failure_threshold": self._failure_threshold,
            "open_at": open_at,
            "recovery_timeout_seconds": self._recovery_timeout,
        }

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _on_success(self) -> None:
        state = self._get_state()
        if state == _HALF_OPEN:
            logger.info("Circuit breaker recovered → CLOSED", name=self._name)
            self._set_state(_CLOSED)
            self._set_failures(0)

    def _on_failure(self) -> None:
        failures = self._increment_failures()
        logger.warning(
            "Circuit breaker failure recorded",
            name=self._name,
            failures=failures,
            threshold=self._failure_threshold,
        )
        if failures >= self._failure_threshold:
            if self._get_state() != _OPEN:
                logger.error("Circuit breaker OPEN", name=self._name, failures=failures)
                self._set_state(_OPEN)
                self._set_open_at(time.time())

    # ------------------------------------------------------------------
    # Redis helpers (fall back to local state on Redis failure)
    # ------------------------------------------------------------------

    def _get_state(self) -> str:
        if self._redis is None:
            return self._local_state
        try:
            val = self._redis.get(self._state_key)
            return val if val else _CLOSED
        except Exception:
            return self._local_state

    def _set_state(self, state: str) -> None:
        self._local_state = state
        if self._redis is None:
            return
        try:
            self._redis.set(self._state_key, state, ex=self._recovery_timeout * 10)
        except Exception:
            pass

    def _get_failures(self) -> int:
        if self._redis is None:
            return self._local_failures
        try:
            val = self._redis.get(self._failures_key)
            return int(val) if val else 0
        except Exception:
            return self._local_failures

    def _set_failures(self, n: int) -> None:
        self._local_failures = n
        if self._redis is None:
            return
        try:
            self._redis.set(self._failures_key, n, ex=self._window_seconds)
        except Exception:
            pass

    def _increment_failures(self) -> int:
        self._local_failures += 1
        if self._redis is None:
            return self._local_failures
        try:
            pipe = self._redis.pipeline()
            pipe.incr(self._failures_key)
            pipe.expire(self._failures_key, self._window_seconds)
            results = pipe.execute()
            return int(results[0])
        except Exception:
            return self._local_failures

    def _get_open_at(self) -> float | None:
        if self._redis is None:
            return self._local_open_at
        try:
            val = self._redis.get(self._open_at_key)
            return float(val) if val else None
        except Exception:
            return self._local_open_at

    def _set_open_at(self, ts: float) -> None:
        self._local_open_at = ts
        if self._redis is None:
            return
        try:
            self._redis.set(
                self._open_at_key, ts, ex=self._recovery_timeout * 10
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Pre-built breakers — import these in service modules
# ---------------------------------------------------------------------------

def _build_redis() -> Any:
    try:
        import redis as redis_lib
        from apps.api.config import get_settings
        return redis_lib.from_url(get_settings().redis_url)
    except Exception:
        return None


def openai_breaker() -> CircuitBreaker:
    """Circuit breaker for OpenAI API calls (5 failures/2min → 60s open)."""
    return CircuitBreaker(
        redis_client=_build_redis(),
        name="openai-embeddings",
        failure_threshold=5,
        recovery_timeout=60,
        window_seconds=120,
        max_retries=3,
        retry_min_wait=1.0,
        retry_max_wait=30.0,
    )


def slack_breaker() -> CircuitBreaker:
    """Circuit breaker for Slack webhook calls (3 failures/5min → 120s open)."""
    return CircuitBreaker(
        redis_client=_build_redis(),
        name="slack-webhook",
        failure_threshold=3,
        recovery_timeout=120,
        window_seconds=300,
        max_retries=2,
        retry_min_wait=2.0,
        retry_max_wait=15.0,
    )


def resend_breaker() -> CircuitBreaker:
    """Circuit breaker for Resend email API (3 failures/5min → 120s open)."""
    return CircuitBreaker(
        redis_client=_build_redis(),
        name="resend-email",
        failure_threshold=3,
        recovery_timeout=120,
        window_seconds=300,
        max_retries=2,
        retry_min_wait=2.0,
        retry_max_wait=15.0,
    )
