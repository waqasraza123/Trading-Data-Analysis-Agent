import pytest
from pydantic import SecretStr

from app.config import AppEnvironment, Settings, build_async_database_url


def test_settings_load_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env == AppEnvironment.DEVELOPMENT
    assert settings.api_prefix == ""
    assert settings.database_url is None
    assert settings.redis_url is None
    assert settings.openai_api_key is None
    assert settings.cors_allowed_origins == []
    assert settings.cors_allow_credentials is False
    assert settings.auth_enabled is False
    assert settings.admin_api_key is None
    assert settings.api_key_header_name == "x-admin-api-key"
    assert settings.rate_limit_enabled is False
    assert settings.live_feed_api_key is None
    assert settings.seed_default_workspace_name is None
    assert settings.seed_default_admin_email is None
    assert settings.seed_default_admin_name is None


def test_settings_validate_api_prefix() -> None:
    settings = Settings(_env_file=None, api_prefix="/api/v1/")

    assert settings.api_prefix == "/api/v1"


def test_settings_reject_invalid_api_prefix() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, api_prefix="api/v1")


def test_settings_parse_cors_allowed_origins() -> None:
    settings = Settings(
        _env_file=None,
        cors_allowed_origins="http://localhost:3000, https://app.example.com",
    )

    assert settings.cors_allowed_origins == [
        "http://localhost:3000",
        "https://app.example.com",
    ]


def test_auth_enabled_requires_admin_api_key() -> None:
    with pytest.raises(ValueError, match="ADMIN_API_KEY"):
        Settings(_env_file=None, auth_enabled=True)


def test_production_rejects_wildcard_cors_origin() -> None:
    with pytest.raises(ValueError, match="CORS_ALLOWED_ORIGINS"):
        Settings(
            _env_file=None,
            app_env=AppEnvironment.PRODUCTION,
            cors_allowed_origins="*",
        )


def test_build_async_database_url_for_neon_postgres_url() -> None:
    database_url = build_async_database_url(
        SecretStr("postgresql://user:password@example.neon.tech/dbname")
    )

    assert database_url == "postgresql+asyncpg://user:password@example.neon.tech/dbname"


def test_build_async_database_url_normalizes_neon_pooler_ssl_query() -> None:
    database_url = build_async_database_url(
        SecretStr(
            "postgresql://user:password@example.neon.tech/dbname"
            "?sslmode=require&channel_binding=require"
        )
    )

    assert database_url == (
        "postgresql+asyncpg://user:password@example.neon.tech/dbname?ssl=require"
    )
