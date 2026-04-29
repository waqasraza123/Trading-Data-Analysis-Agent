from enum import StrEnum
from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    api_prefix: str = ""
    log_level: LogLevel = LogLevel.INFO
    database_url: SecretStr | None = None
    redis_url: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    live_feed_provider: str | None = None
    live_feed_api_key: SecretStr | None = None
    service_name: str = "trading-intelligence-api"
    service_title: str = "Trading Intelligence API"
    service_version: str = "0.1.0"

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized_value = value.strip()
        if normalized_value in {"", "/"}:
            return ""
        if not normalized_value.startswith("/"):
            msg = "API_PREFIX must be empty or start with /"
            raise ValueError(msg)
        return normalized_value.rstrip("/")


def build_async_database_url(database_url: SecretStr) -> str:
    raw_database_url = database_url.get_secret_value()
    if raw_database_url.startswith("postgresql+asyncpg://"):
        return raw_database_url
    if raw_database_url.startswith("postgresql://"):
        return raw_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if raw_database_url.startswith("postgres://"):
        return raw_database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return raw_database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
