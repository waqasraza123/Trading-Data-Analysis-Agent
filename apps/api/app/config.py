from enum import StrEnum
from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
        return normalize_asyncpg_query(raw_database_url)
    if raw_database_url.startswith("postgresql://"):
        return normalize_asyncpg_query(
            raw_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        )
    if raw_database_url.startswith("postgres://"):
        return normalize_asyncpg_query(
            raw_database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        )
    return raw_database_url


def normalize_asyncpg_query(database_url: str) -> str:
    url = urlsplit(database_url)
    query_pairs = parse_qsl(url.query, keep_blank_values=True)
    normalized_pairs: list[tuple[str, str]] = []
    ssl_required = False
    for key, value in query_pairs:
        if key == "sslmode":
            ssl_required = value in {"require", "prefer", "verify-ca", "verify-full"}
            continue
        if key == "channel_binding":
            continue
        normalized_pairs.append((key, value))
    if ssl_required and not any(key == "ssl" for key, _ in normalized_pairs):
        normalized_pairs.append(("ssl", "require"))
    return urlunsplit(
        (
            url.scheme,
            url.netloc,
            url.path,
            urlencode(normalized_pairs),
            url.fragment,
        )
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
