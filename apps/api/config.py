"""Application settings loaded from environment variables."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    log_level: str = "DEBUG"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]

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

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
