"""Application settings loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )

    # App
    app_env: str = "development"
    log_level: str = "DEBUG"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://hallucin8:hallucin8@localhost:5432/hallucin8"
    database_url_sync: str = "postgresql+psycopg2://hallucin8:hallucin8@localhost:5432/hallucin8"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "hallucin8pass"

    # Kafka / Redpanda
    kafka_bootstrap_servers: str = "localhost:9092"

    # LLM probing
    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    # Cost cap
    max_daily_spend_usd: float = 5.00

    # Auth
    jwt_secret: str = "change-me-in-production"

    # Resend email delivery (Sprint 8)
    resend_api_key: str = ""
    resend_from_email: str = "reports@hallucin8.io"

    # Slack alerts (Sprint 8) — org-level default; per-webhook URLs override this
    slack_webhook_url: str = ""

    # Alert rule cooldown: minimum minutes between two firings of the same rule
    alert_rule_cooldown_minutes: int = 60

    # Sentry DSN (Sprint 9) — leave empty to disable Sentry
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # Tiered probing (Sprint 9)
    # probe_daily_model:  LLM used for daily scans  (cheaper/faster)
    # probe_weekly_model: LLM used for full weekly scan (higher quality)
    probe_daily_model: str = "gpt-4o-mini"
    probe_weekly_model: str = "gemini-1.5-pro"

    # GCS bucket for daily backups (Sprint 9)
    gcs_backup_bucket: str = ""
    gcs_backup_prefix: str = "hallucin8/backups"

    # Sprint 10 — Beta Launch
    # Internal admin panel secret — set to a strong random value in prod
    admin_secret: str = "change-me-admin-secret"
    # PostHog project API key
    posthog_api_key: str = ""
    # GitHub token for automatic issue reporting from error boundary
    github_issue_token: str = ""
    # Intercom app ID
    intercom_app_id: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse cors_origins — accepts comma-separated URLs or a JSON array string."""
        import json as _json
        v = self.cors_origins.strip()
        if not v:
            return ["http://localhost:3000"]
        try:
            parsed = _json.loads(v)
            if isinstance(parsed, list):
                return [o.strip() for o in parsed if o.strip()]
        except _json.JSONDecodeError:
            pass
        return [o.strip() for o in v.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
