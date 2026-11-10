"""Settings read from environment variables. Nothing secret has a default."""

from __future__ import annotations

from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
