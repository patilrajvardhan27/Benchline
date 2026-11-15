"""Settings read from environment variables. Nothing secret has a default."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ML_", extra="ignore")

    database_url: str = "postgresql://benchline@localhost:5432/benchline"
    kafka_bootstrap: str = "localhost:9092"
    consumer_enabled: bool = True
    consumer_group: str = "ml-anomaly"
    topic: str = "pricing.price-point-recorded.v1"
    z_threshold: float = 3.5
    min_group_history: int = 8
    history_weeks: int = 52

    # Ask Benchline. Tokens are checked like the pricing API checks them: a dev secret locally,
    # the identity provider's keys otherwise. With neither, the agent refuses every request.
    dev_jwt_secret: str = Field(default="", validation_alias="DEV_JWT_SECRET")
    oidc_issuer_uri: str = Field(default="", validation_alias="OIDC_ISSUER_URI")
    cors_origins: str = ""            # comma-separated browser origins allowed to call the agent
    agent_runs_per_hour: int = 20     # per user
    agent_daily_usd: float = 1.0      # model spend across all users, reset at midnight UTC
    agent_snapshot_dir: str = ""      # read the demo snapshot instead of Postgres


@lru_cache
def get_settings() -> Settings:
    return Settings()
