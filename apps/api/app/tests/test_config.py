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
    assert settings.openai_base_url is None
    assert settings.anthropic_api_key is None
    assert settings.llm_explanations_enabled is False
    assert settings.llm_provider == "mock"
    assert settings.llm_model == "gpt-4o-mini"
    assert settings.llm_store_inputs is False
    assert settings.llm_store_outputs is True
    assert settings.llm_reasoning_enabled is False
    assert settings.llm_default_provider == "mock"
    assert settings.llm_default_model == "mock-scenario-v1"
    assert settings.llm_provider_timeout_seconds == 12
    assert settings.llm_temperature == 0.2
    assert settings.scenario_ensemble_version == "v1"
    assert settings.scenario_ensemble_default_provider == "mock"
    assert settings.scenario_ensemble_max_providers == 3
    assert str(settings.scenario_ensemble_min_agreement_ratio) == "0.6000"
    assert settings.news_correlation_pre_event_minutes == 5
    assert settings.news_correlation_post_event_minutes == 30
    assert settings.news_correlation_max_events_per_signal == 10
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
    assert settings.notification_worker_enabled is False
    assert settings.notification_worker_batch_size == 100
    assert settings.market_scan_worker_enabled is False
    assert settings.market_scan_worker_poll_seconds == 30
    assert settings.market_scan_worker_batch_size == 10
    assert settings.market_scan_default_lookback_minutes == 60
    assert settings.market_scan_default_interval_seconds == 60
    assert settings.scanner_preset_version == "v1"
    assert settings.provider_polling_timeout_seconds == 20
    assert settings.provider_polling_max_candles_per_request == 1000
    assert (
        settings.provider_polling_user_agent
        == "trading-intelligence-api-provider-polling/0.1"
    )
    assert settings.binance_public_rest_base_url == "https://api.binance.com"
    assert settings.provider_health_version == "v1"
    assert settings.provider_health_fresh_seconds_1m == 180
    assert settings.provider_health_fresh_seconds_5m == 600
    assert settings.provider_health_fresh_seconds_15m == 1800
    assert settings.provider_health_fresh_seconds_1h == 7200
    assert settings.provider_health_max_failures_degraded == 2
    assert settings.provider_health_max_failures_failing == 5
    assert settings.signal_priority_version == "v1"
    assert str(settings.signal_priority_high_threshold) == "0.75"
    assert str(settings.signal_priority_medium_threshold) == "0.55"
    assert str(settings.signal_priority_stale_penalty) == "0.30"
    assert str(settings.signal_priority_conflict_penalty) == "0.25"
    assert str(settings.signal_priority_review_required_threshold) == "0.50"
    assert settings.preference_profile_default_max_stale_seconds == 7200
    assert settings.chart_unsupported_rejection_enabled is True
    assert settings.audit_timeline_max_events == 200
    assert settings.audit_timeline_max_audit_events == 100
    assert settings.audit_timeline_max_artifacts == 200
    assert settings.audit_timeline_redaction_enabled is True
    assert settings.intelligence_quality_gate_version == "quality_gates_v1"
    assert settings.intelligence_quality_shadow_version == "shadow_profiles_v1"
    assert str(settings.intelligence_quality_strong_threshold) == "0.9000"
    assert str(settings.intelligence_quality_acceptable_threshold) == "0.7500"
    assert str(settings.intelligence_quality_review_threshold) == "0.5000"
    assert settings.market_regime_version == "market_regime_v1"
    assert str(settings.market_regime_min_confidence) == "0.5000"
    assert str(settings.market_regime_strong_data_quality) == "0.8500"
    assert str(settings.market_regime_acceptable_data_quality) == "0.6500"
    assert settings.historical_case_vector_version == "historical_case_vector_v1"
    assert settings.historical_case_default_limit == 10
    assert settings.historical_case_max_limit == 50
    assert str(settings.historical_case_min_score) == "0.5000"
    assert settings.decision_readiness_assessment_version == "decision_readiness_v1"
    assert str(settings.decision_readiness_ready_threshold) == "0.8500"
    assert str(settings.decision_readiness_review_threshold) == "0.6500"
    assert settings.worker_supervisor_components == []
    assert settings.worker_supervisor_shutdown_timeout_seconds == 20


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


def test_production_rate_limit_requires_redis_url() -> None:
    with pytest.raises(ValueError, match="REDIS_URL"):
        Settings(
            _env_file=None,
            app_env=AppEnvironment.PRODUCTION,
            rate_limit_enabled=True,
        )


def test_production_rate_limit_accepts_redis_url() -> None:
    settings = Settings(
        _env_file=None,
        app_env=AppEnvironment.PRODUCTION,
        rate_limit_enabled=True,
        redis_url=SecretStr("redis://localhost:6379/0"),
    )

    assert settings.redis_url is not None


def test_production_rejects_wildcard_cors_origin() -> None:
    with pytest.raises(ValueError, match="CORS_ALLOWED_ORIGINS"):
        Settings(
            _env_file=None,
            app_env=AppEnvironment.PRODUCTION,
            cors_allowed_origins="*",
        )


def test_quality_thresholds_must_be_ordered() -> None:
    with pytest.raises(ValueError, match="INTELLIGENCE_QUALITY_STRONG_THRESHOLD"):
        Settings(
            _env_file=None,
            intelligence_quality_strong_threshold="0.7000",
            intelligence_quality_acceptable_threshold="0.8000",
        )


def test_production_requires_audit_timeline_redaction() -> None:
    with pytest.raises(ValueError, match="AUDIT_TIMELINE_REDACTION_ENABLED"):
        Settings(
            _env_file=None,
            app_env=AppEnvironment.PRODUCTION,
            audit_timeline_redaction_enabled=False,
        )


def test_chart_unsupported_rejection_cannot_be_disabled() -> None:
    with pytest.raises(ValueError, match="CHART_UNSUPPORTED_REJECTION_ENABLED"):
        Settings(_env_file=None, chart_unsupported_rejection_enabled=False)


def test_advanced_context_threshold_settings_must_be_ordered() -> None:
    with pytest.raises(ValueError, match="MARKET_REGIME_STRONG_DATA_QUALITY"):
        Settings(
            _env_file=None,
            market_regime_strong_data_quality="0.6000",
            market_regime_acceptable_data_quality="0.7000",
        )
    with pytest.raises(ValueError, match="HISTORICAL_CASE_DEFAULT_LIMIT"):
        Settings(
            _env_file=None,
            historical_case_default_limit=60,
            historical_case_max_limit=50,
        )
    with pytest.raises(ValueError, match="DECISION_READINESS_READY_THRESHOLD"):
        Settings(
            _env_file=None,
            decision_readiness_ready_threshold="0.6000",
            decision_readiness_review_threshold="0.7000",
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
