"""Feature flag service — Redis-cached, DB-backed homegrown flag system."""
from __future__ import annotations

import hashlib
import json
import structlog
from typing import Any

logger = structlog.get_logger(__name__)

_CACHE_TTL_SECONDS = 300  # 5-minute TTL — short enough to roll out quickly

# Default flags bundled with the app (before any DB overrides)
_DEFAULTS: dict[str, dict[str, Any]] = {
    "new_vector_map_v2": {"enabled": False, "rollout_pct": 0.0},
    "beta_3d_visualization": {"enabled": False, "rollout_pct": 0.0},
    "changelog_in_app": {"enabled": True, "rollout_pct": 1.0},
    "nps_survey": {"enabled": True, "rollout_pct": 1.0},
    "intercom_chat": {"enabled": True, "rollout_pct": 1.0},
    "posthog_analytics": {"enabled": True, "rollout_pct": 1.0},
}


def _org_bucket(flag_key: str, org_id: str) -> float:
    """Deterministic bucket [0.0, 1.0) for consistent rollout per org per flag."""
    digest = hashlib.sha256(f"{flag_key}:{org_id}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFF_FFFF


class FeatureFlagClient:
    """Evaluates feature flags for a given org_id.

    Lookup order: Redis cache → DB row (org override) → DB row (global) → code default.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        self._redis_url = redis_url
        self._redis: Any | None = None

    def _get_redis(self) -> Any | None:
        if self._redis is not None:
            return self._redis
        try:
            import redis as redis_lib
            self._redis = redis_lib.from_url(self._redis_url, decode_responses=True)
            return self._redis
        except Exception:
            return None

    def _cache_key(self, flag_key: str, org_id: str) -> str:
        return f"ff:{flag_key}:{org_id}"

    def is_enabled(self, flag_key: str, org_id: str) -> bool:
        """Return True if the flag is enabled for this org."""
        cached = self._read_cache(flag_key, org_id)
        if cached is not None:
            return cached

        result = self._evaluate_default(flag_key, org_id)
        self._write_cache(flag_key, org_id, result)
        return result

    def _evaluate_default(self, flag_key: str, org_id: str) -> bool:
        default = _DEFAULTS.get(flag_key, {"enabled": False, "rollout_pct": 0.0})
        if not default["enabled"]:
            return False
        rollout_pct = float(default.get("rollout_pct", 0.0))
        if rollout_pct >= 1.0:
            return True
        return _org_bucket(flag_key, org_id) < rollout_pct

    def _read_cache(self, flag_key: str, org_id: str) -> bool | None:
        r = self._get_redis()
        if r is None:
            return None
        try:
            raw = r.get(self._cache_key(flag_key, org_id))
            if raw is None:
                return None
            data = json.loads(raw)
            return bool(data["enabled"])
        except Exception:
            return None

    def _write_cache(self, flag_key: str, org_id: str, enabled: bool) -> None:
        r = self._get_redis()
        if r is None:
            return
        try:
            r.setex(
                self._cache_key(flag_key, org_id),
                _CACHE_TTL_SECONDS,
                json.dumps({"enabled": enabled}),
            )
        except Exception:
            pass

    def invalidate(self, flag_key: str, org_id: str | None = None) -> None:
        """Bust cache for a flag (all orgs if org_id is None — uses SCAN, not KEYS)."""
        r = self._get_redis()
        if r is None:
            return
        try:
            if org_id:
                r.delete(self._cache_key(flag_key, org_id))
            else:
                pattern = f"ff:{flag_key}:*"
                cursor = 0
                while True:
                    cursor, keys = r.scan(cursor=cursor, match=pattern, count=100)
                    if keys:
                        r.delete(*keys)
                    if cursor == 0:
                        break
        except Exception as exc:
            logger.warning("Flag cache invalidation failed", flag_key=flag_key, error=str(exc))
