from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from typing import Self
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, SecretStr, field_validator, model_validator
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
    openai_base_url: str | None = None
    anthropic_api_key: SecretStr | None = None
    llm_explanations_enabled: bool = False
    llm_provider: str = "mock"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = Field(default=12.0, gt=0)
    llm_max_input_tokens: int = Field(default=1800, ge=1)
    llm_max_output_tokens: int = Field(default=450, ge=1)
    llm_store_inputs: bool = False
    llm_store_outputs: bool = True
    llm_reasoning_enabled: bool = False
    llm_default_provider: str = "mock"
    llm_default_model: str = "mock-scenario-v1"
    llm_provider_timeout_seconds: float = Field(default=12.0, gt=0)
    llm_temperature: float = Field(default=0.2, ge=0, le=2)
    cors_allowed_origins: list[str] = Field(default_factory=list)
    cors_allow_credentials: bool = False
    auth_enabled: bool = False
    admin_api_key: SecretStr | None = None
    api_key_header_name: str = "x-admin-api-key"
    rate_limit_enabled: bool = False
    rate_limit_requests_per_minute: int = Field(default=60, ge=1)
    max_request_body_bytes: int = Field(default=1_048_576, ge=1)
    max_upload_file_bytes: int = Field(default=10_485_760, ge=1)
    live_feed_provider: str | None = None
    live_feed_api_key: SecretStr | None = None
    live_feed_reconnect_initial_seconds: float = Field(default=1, gt=0)
    live_feed_reconnect_max_seconds: float = Field(default=60, gt=0)
    live_feed_reconnect_multiplier: float = Field(default=2, gt=1)
    live_feed_stale_message_seconds: int = Field(default=180, ge=1)
    live_feed_stale_final_candle_seconds: int = Field(default=300, ge=1)
    live_feed_worker_poll_seconds: float = Field(default=10, gt=0)
    news_correlation_pre_event_minutes: int = Field(default=5, ge=0, le=1440)
    news_correlation_post_event_minutes: int = Field(default=30, ge=1, le=1440)
    news_correlation_max_events_per_signal: int = Field(default=10, ge=1, le=100)
    outcome_default_horizons_minutes: list[int] = Field(default_factory=lambda: [5, 15, 30, 60])
    outcome_min_future_candles: int = Field(default=3, ge=1, le=500)
    outcome_evaluation_version: str = "v1"
    profile_diagnostics_minimum_sample_size: int = Field(default=20, ge=1, le=10000)
    profile_diagnostics_strong_follow_through_rate: Decimal = Field(
        default=Decimal("0.65"),
        ge=0,
        le=1,
    )
    profile_diagnostics_high_reversal_rate: Decimal = Field(default=Decimal("0.35"), ge=0, le=1)
    profile_diagnostics_high_no_follow_through_rate: Decimal = Field(
        default=Decimal("0.40"),
        ge=0,
        le=1,
    )
    profile_diagnostics_confidence_misalignment_threshold: Decimal = Field(
        default=Decimal("0.45"),
        ge=0,
        le=1,
    )
    reasoning_action_worker_enabled: bool = False
    reasoning_action_worker_poll_seconds: float = Field(default=10, gt=0)
    reasoning_action_worker_batch_size: int = Field(default=25, ge=1, le=500)
    reasoning_action_worker_max_concurrency: int = Field(default=4, ge=1, le=50)
    reasoning_action_worker_lock_seconds: int = Field(default=120, ge=1)
    reasoning_action_worker_max_attempts: int = Field(default=3, ge=1, le=100)
    reasoning_action_worker_jitter_seconds: float = Field(default=2, ge=0)
    service_name: str = "trading-intelligence-api"
    service_title: str = "Trading Intelligence API"
    service_version: str = "0.1.0"
    seed_default_workspace_name: str | None = None
    seed_default_admin_email: str | None = None
    seed_default_admin_name: str | None = None

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

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("api_key_header_name")
    @classmethod
    def validate_api_key_header_name(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if normalized_value == "":
            msg = "API_KEY_HEADER_NAME must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("live_feed_provider")
    @classmethod
    def normalize_live_feed_provider(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized_value = value.strip().lower()
        return normalized_value or None

    @field_validator("llm_provider")
    @classmethod
    def normalize_llm_provider(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("llm_default_provider")
    @classmethod
    def normalize_llm_default_provider(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("llm_model")
    @classmethod
    def normalize_llm_model(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "LLM_MODEL must not be empty when LLM explanations are enabled"
            raise ValueError(msg)
        return normalized_value

    @field_validator("llm_default_model")
    @classmethod
    def normalize_llm_default_model(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "LLM_DEFAULT_MODEL must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("openai_base_url")
    @classmethod
    def normalize_openai_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized_value = value.strip().rstrip("/")
        return normalized_value or None

    @field_validator("outcome_default_horizons_minutes", mode="before")
    @classmethod
    def parse_outcome_default_horizons_minutes(cls, value: object) -> object:
        if isinstance(value, str):
            return [int(item.strip()) for item in value.split(",") if item.strip()]
        return value

    @field_validator("outcome_default_horizons_minutes")
    @classmethod
    def validate_outcome_default_horizons_minutes(cls, value: list[int]) -> list[int]:
        normalized = sorted({horizon for horizon in value if horizon > 0})
        if not normalized:
            msg = "OUTCOME_DEFAULT_HORIZONS_MINUTES must contain at least one positive horizon"
            raise ValueError(msg)
        return normalized

    @field_validator("outcome_evaluation_version")
    @classmethod
    def validate_outcome_evaluation_version(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "OUTCOME_EVALUATION_VERSION must not be empty"
            raise ValueError(msg)
        return normalized_value

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        if self.auth_enabled and secret_is_empty(self.admin_api_key):
            msg = "ADMIN_API_KEY is required when AUTH_ENABLED=true"
            raise ValueError(msg)
        if self.app_env == AppEnvironment.PRODUCTION and "*" in self.cors_allowed_origins:
            msg = "CORS_ALLOWED_ORIGINS must not include * in production"
            raise ValueError(msg)
        if (
            self.app_env == AppEnvironment.PRODUCTION
            and self.cors_allow_credentials
            and not self.cors_allowed_origins
        ):
            msg = "CORS_ALLOWED_ORIGINS is required in production when credentials are enabled"
            raise ValueError(msg)
        if provider_requires_api_key(self.live_feed_provider) and secret_is_empty(
            self.live_feed_api_key
        ):
            msg = "LIVE_FEED_API_KEY is required for the selected live feed provider"
            raise ValueError(msg)
        return self


def secret_is_empty(value: SecretStr | None) -> bool:
    if value is None:
        return True
    return value.get_secret_value().strip() == ""


def provider_requires_api_key(provider: str | None) -> bool:
    if provider is None:
        return False
    return provider in {"alpaca", "polygon", "twelve_data"}


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
