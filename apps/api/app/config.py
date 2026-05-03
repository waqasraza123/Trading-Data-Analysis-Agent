from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from typing import Self
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


class WorkerSupervisorComponent(StrEnum):
    LIVE_FEED = "live_feed"
    STALE_MONITOR = "stale_monitor"
    REASONING_ACTIONS = "reasoning_actions"
    NOTIFICATIONS = "notifications"
    MARKET_SCANS = "market_scans"


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
    scenario_ensemble_version: str = "v1"
    scenario_ensemble_default_provider: str = "mock"
    scenario_ensemble_max_providers: int = Field(default=3, ge=1, le=10)
    scenario_ensemble_min_agreement_ratio: Decimal = Field(
        default=Decimal("0.6000"),
        ge=0,
        le=1,
    )
    scenario_outcome_evaluation_version: str = "v1"
    scenario_outcome_default_horizon_minutes: int = Field(default=30, gt=0)
    scenario_outcome_support_threshold: Decimal = Field(default=Decimal("0.6000"), ge=0, le=1)
    explanation_comparison_version: str = "v1"
    explanation_comparison_alignment_threshold: Decimal = Field(
        default=Decimal("0.7500"),
        ge=0,
        le=1,
    )
    explanation_comparison_review_threshold: Decimal = Field(
        default=Decimal("0.5000"),
        ge=0,
        le=1,
    )
    backtest_experiment_version: str = "v1"
    backtest_experiment_default_limit: int = Field(default=100, ge=1, le=5000)
    backtest_experiment_max_limit: int = Field(default=1000, ge=1, le=10000)
    backtest_experiment_minimum_sample_size: int = Field(default=20, ge=1, le=10000)
    walk_forward_validation_version: str = "v1"
    walk_forward_default_window_days: int = Field(default=30, ge=1, le=3660)
    walk_forward_minimum_sample_size: int = Field(default=20, ge=1, le=10000)
    walk_forward_degradation_threshold: Decimal = Field(default=Decimal("0.20"), ge=0, le=1)
    walk_forward_improvement_threshold: Decimal = Field(default=Decimal("0.20"), ge=0, le=1)
    cohort_drift_version: str = "v1"
    cohort_drift_minimum_sample_size: int = Field(default=20, ge=1, le=10000)
    cohort_drift_mild_threshold: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)
    cohort_drift_moderate_threshold: Decimal = Field(default=Decimal("0.20"), ge=0, le=1)
    cohort_drift_severe_threshold: Decimal = Field(default=Decimal("0.35"), ge=0, le=1)
    cohort_drift_default_baseline_days: int = Field(default=90, ge=1, le=3660)
    cohort_drift_default_comparison_days: int = Field(default=30, ge=1, le=3660)
    capability_registry_default_version: str = "v1"
    synthetic_fixtures_api_enabled: bool = False
    synthetic_fixtures_default_seed: int = Field(default=12345, ge=0)
    ai_intelligence_enabled: bool = False
    ai_intelligence_max_output_tokens: int = Field(default=700, ge=1)
    market_session_version: str = "v1"
    market_session_default_timezone: str = "UTC"
    chart_ocr_enabled: bool = False
    chart_ocr_provider: str = "google_vision"
    chart_ocr_timeout_seconds: float = Field(default=10.0, gt=0)
    chart_ocr_min_confidence: Decimal = Field(default=Decimal("0.6500"), ge=0, le=1)
    chart_image_min_extraction_confidence: Decimal = Field(default=Decimal("0.7500"), ge=0, le=1)
    chart_unsupported_rejection_enabled: bool = True
    audit_timeline_max_events: int = Field(default=200, ge=1, le=500)
    audit_timeline_max_audit_events: int = Field(default=100, ge=1, le=500)
    audit_timeline_max_artifacts: int = Field(default=200, ge=1, le=500)
    audit_timeline_redaction_enabled: bool = True
    intelligence_quality_gate_version: str = "quality_gates_v1"
    intelligence_quality_shadow_version: str = "shadow_profiles_v1"
    intelligence_quality_strong_threshold: Decimal = Field(default=Decimal("0.9000"), ge=0, le=1)
    intelligence_quality_acceptable_threshold: Decimal = Field(
        default=Decimal("0.7500"),
        ge=0,
        le=1,
    )
    intelligence_quality_review_threshold: Decimal = Field(
        default=Decimal("0.5000"),
        ge=0,
        le=1,
    )
    market_regime_version: str = "market_regime_v1"
    market_regime_min_confidence: Decimal = Field(default=Decimal("0.5000"), ge=0, le=1)
    market_regime_strong_data_quality: Decimal = Field(default=Decimal("0.8500"), ge=0, le=1)
    market_regime_acceptable_data_quality: Decimal = Field(
        default=Decimal("0.6500"),
        ge=0,
        le=1,
    )
    historical_case_vector_version: str = "historical_case_vector_v1"
    historical_case_default_limit: int = Field(default=10, ge=1, le=500)
    historical_case_max_limit: int = Field(default=50, ge=1, le=500)
    historical_case_min_score: Decimal = Field(default=Decimal("0.5000"), ge=0, le=1)
    decision_readiness_assessment_version: str = "decision_readiness_v1"
    decision_readiness_ready_threshold: Decimal = Field(default=Decimal("0.8500"), ge=0, le=1)
    decision_readiness_review_threshold: Decimal = Field(default=Decimal("0.6500"), ge=0, le=1)
    advanced_feature_pack_version: str = "v1"
    advanced_feature_min_candle_count: int = Field(default=20, ge=1)
    advanced_feature_swing_lookback: int = Field(default=3, ge=1, le=20)
    advanced_feature_zone_lookback: int = Field(default=80, ge=5)
    advanced_feature_compression_lookback: int = Field(default=20, ge=4)
    advanced_feature_expansion_multiplier: Decimal = Field(default=Decimal("1.5"), gt=0)
    advanced_feature_wick_pressure_threshold: Decimal = Field(
        default=Decimal("0.55"),
        ge=0,
        le=1,
    )
    advanced_feature_movement_efficiency_threshold: Decimal = Field(
        default=Decimal("0.60"),
        ge=0,
        le=1,
    )
    rule_pack_default_key: str = "default_deterministic_rules"
    rule_pack_default_version: str = "v1"
    reproducibility_manifest_version: str = "v1"
    event_study_version: str = "v1"
    event_study_default_pre_event_minutes: int = Field(default=60, ge=0)
    event_study_default_post_event_minutes: int = Field(default=240, ge=1)
    event_study_min_candles: int = Field(default=5, ge=1)
    event_study_strong_reaction_multiplier: Decimal = Field(default=Decimal("2.0"), gt=0)
    event_study_moderate_reaction_multiplier: Decimal = Field(default=Decimal("1.25"), gt=0)
    confidence_calibration_version: str = "v1"
    confidence_calibration_default_bins: int = Field(default=10, ge=2, le=100)
    confidence_calibration_minimum_sample_size: int = Field(default=20, ge=1)
    confidence_calibration_overconfident_threshold: Decimal = Field(
        default=Decimal("0.15"),
        ge=0,
        le=1,
    )
    confidence_calibration_underconfident_threshold: Decimal = Field(
        default=Decimal("0.15"),
        ge=0,
        le=1,
    )
    webhook_outbox_payload_version: str = "v1"
    webhook_outbox_default_status: str = "held"
    webhook_outbox_max_payload_bytes: int = Field(default=32768, ge=1024)
    context_pack_max_evidence_rows: int = Field(default=50, ge=1, le=500)
    context_pack_max_risk_notes: int = Field(default=50, ge=1, le=500)
    context_pack_max_audit_events: int = Field(default=100, ge=1, le=1000)
    context_pack_max_outcomes: int = Field(default=20, ge=1, le=500)
    context_pack_max_scenarios: int = Field(default=10, ge=1, le=100)
    context_pack_max_action_items: int = Field(default=50, ge=1, le=500)
    context_pack_max_news_correlations: int = Field(default=20, ge=1, le=500)
    context_pack_max_text_length: int = Field(default=4000, ge=100, le=20000)
    context_pack_schema_version: str = "v1"
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
    provider_polling_timeout_seconds: int = Field(default=20, ge=1)
    provider_polling_max_candles_per_request: int = Field(default=1000, ge=1, le=5000)
    provider_polling_user_agent: str = "trading-intelligence-api-provider-polling/0.1"
    binance_public_rest_base_url: str = "https://api.binance.com"
    candle_gap_recovery_version: str = "v1"
    candle_gap_recovery_max_gaps: int = Field(default=500, ge=1, le=10000)
    candle_gap_recovery_max_range_days: int = Field(default=30, ge=1, le=366)
    data_quality_version: str = "v1"
    data_quality_strong_threshold: Decimal = Field(default=Decimal("0.95"), ge=0, le=1)
    data_quality_acceptable_threshold: Decimal = Field(default=Decimal("0.85"), ge=0, le=1)
    data_quality_degraded_threshold: Decimal = Field(default=Decimal("0.70"), ge=0, le=1)
    data_quality_outlier_range_multiplier: Decimal = Field(default=Decimal("4.0"), gt=0)
    data_quality_stale_live_seconds: int = Field(default=300, ge=1)
    news_correlation_pre_event_minutes: int = Field(default=5, ge=0, le=1440)
    news_correlation_post_event_minutes: int = Field(default=30, ge=1, le=1440)
    news_correlation_max_events_per_signal: int = Field(default=10, ge=1, le=100)
    event_study_version: str = "v1"
    event_study_default_pre_event_minutes: int = Field(default=30, ge=0, le=10080)
    event_study_default_post_event_minutes: int = Field(default=60, ge=1, le=10080)
    event_study_min_candles: int = Field(default=5, ge=1, le=10000)
    event_study_strong_reaction_multiplier: Decimal = Field(default=Decimal("2.0"), gt=0)
    event_study_moderate_reaction_multiplier: Decimal = Field(default=Decimal("1.25"), gt=0)
    outcome_default_horizons_minutes: list[int] = Field(default_factory=lambda: [5, 15, 30, 60])
    outcome_min_future_candles: int = Field(default=3, ge=1, le=500)
    outcome_evaluation_version: str = "v1"
    rule_pack_default_key: str = "core_deterministic"
    rule_pack_default_version: str = "v1"
    reproducibility_manifest_version: str = "v1"
    market_regime_version: str = "v1"
    market_regime_min_confidence: Decimal = Field(default=Decimal("0.50"), ge=0, le=1)
    market_regime_strong_data_quality: Decimal = Field(default=Decimal("0.90"), ge=0, le=1)
    market_regime_acceptable_data_quality: Decimal = Field(default=Decimal("0.75"), ge=0, le=1)
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
    pattern_attribution_version: str = "v1"
    pattern_attribution_minimum_sample_size: int = Field(default=20, ge=1, le=10000)
    pattern_attribution_high_rejection_rate: Decimal = Field(
        default=Decimal("0.50"),
        ge=0,
        le=1,
    )
    pattern_attribution_high_reversal_rate: Decimal = Field(
        default=Decimal("0.35"),
        ge=0,
        le=1,
    )
    profile_governance_default_review_required: bool = True
    profile_governance_component_weight_tolerance: Decimal = Field(
        default=Decimal("0.0001"),
        ge=0,
        le=1,
    )
    confidence_calibration_version: str = "v1"
    confidence_calibration_default_bins: str = "0-0.39,0.40-0.64,0.65-0.79,0.80-1.0"
    confidence_calibration_minimum_sample_size: int = Field(default=20, ge=1, le=10000)
    confidence_calibration_overconfident_threshold: Decimal = Field(
        default=Decimal("0.25"),
        ge=0,
        le=1,
    )
    confidence_calibration_underconfident_threshold: Decimal = Field(
        default=Decimal("0.25"),
        ge=0,
        le=1,
    )
    historical_case_vector_version: str = "v1"
    historical_case_default_limit: int = Field(default=20, ge=1, le=1000)
    historical_case_max_limit: int = Field(default=100, ge=1, le=1000)
    historical_case_min_score: Decimal = Field(default=Decimal("0.40"), ge=0, le=1)
    timeframe_aggregation_version: str = "v1"
    timeframe_aggregation_min_completeness: Decimal = Field(default=Decimal("1.0"), ge=0, le=1)
    timeframe_aggregation_allowed_targets: list[str] = Field(
        default_factory=lambda: ["5m", "15m", "30m", "1h", "4h"]
    )
    multi_timeframe_context_version: str = "v1"
    cross_asset_context_version: str = "v1"
    cross_asset_min_candles: int = Field(default=20, ge=1, le=10000)
    cross_asset_max_compared_symbols: int = Field(default=20, ge=1, le=1000)
    cross_asset_lead_lag_max_offset: int = Field(default=5, ge=0, le=100)
    cross_asset_alignment_threshold: Decimal = Field(default=Decimal("0.60"), ge=0, le=1)
    cross_asset_divergence_threshold: Decimal = Field(default=Decimal("0.60"), ge=0, le=1)
    market_memory_state_version: str = "v1"
    market_memory_fresh_seconds_1m: int = Field(default=180, ge=1)
    market_memory_fresh_seconds_5m: int = Field(default=600, ge=1)
    market_memory_fresh_seconds_15m: int = Field(default=1800, ge=1)
    market_memory_fresh_seconds_1h: int = Field(default=7200, ge=1)
    market_memory_max_context_warnings: int = Field(default=50, ge=1, le=500)
    artifact_graph_version: str = "v1"
    artifact_graph_max_traversal_depth: int = Field(default=8, ge=1, le=64)
    artifact_graph_max_paths: int = Field(default=500, ge=1, le=5000)
    reasoning_action_worker_enabled: bool = False
    reasoning_action_worker_poll_seconds: float = Field(default=10, gt=0)
    reasoning_action_worker_batch_size: int = Field(default=25, ge=1, le=500)
    reasoning_action_worker_max_concurrency: int = Field(default=4, ge=1, le=50)
    reasoning_action_worker_lock_seconds: int = Field(default=120, ge=1)
    reasoning_action_worker_max_attempts: int = Field(default=3, ge=1, le=100)
    reasoning_action_worker_jitter_seconds: float = Field(default=2, ge=0)
    notification_worker_enabled: bool = False
    notification_worker_poll_seconds: float = Field(default=10, gt=0)
    notification_worker_batch_size: int = Field(default=100, ge=1, le=500)
    notification_worker_lock_seconds: int = Field(default=120, ge=1)
    notification_worker_max_attempts: int = Field(default=3, ge=1, le=100)
    notification_worker_jitter_seconds: float = Field(default=2, ge=0)
    notifications_enabled: bool = False
    notification_delivery_timeout_seconds: int = Field(default=10, ge=1, le=120)
    notification_max_payload_bytes: int = Field(default=16000, ge=1024, le=262144)
    notification_dedupe_window_seconds: int = Field(default=3600, ge=0, le=2_592_000)
    notification_default_quiet_hours_timezone: str = "UTC"
    notification_webhook_user_agent: str = "trading-intelligence-notifications/0.1"
    market_scan_worker_enabled: bool = False
    market_scan_worker_poll_seconds: float = Field(default=30, gt=0)
    market_scan_worker_batch_size: int = Field(default=10, ge=1, le=500)
    market_scan_default_lookback_minutes: int = Field(default=60, ge=1, le=43200)
    market_scan_default_interval_seconds: int = Field(default=60, ge=1)
    worker_supervisor_components: list[WorkerSupervisorComponent] = Field(default_factory=list)
    worker_supervisor_shutdown_timeout_seconds: float = Field(default=20, gt=0)
    profile_simulation_max_signals: int = Field(default=500, ge=1, le=5000)
    profile_simulation_version: str = "v1"
    data_quality_version: str = "v1"
    data_quality_strong_threshold: Decimal = Field(default=Decimal("0.9500"), ge=0, le=1)
    data_quality_acceptable_threshold: Decimal = Field(default=Decimal("0.8500"), ge=0, le=1)
    data_quality_degraded_threshold: Decimal = Field(default=Decimal("0.7000"), ge=0, le=1)
    data_quality_outlier_range_multiplier: Decimal = Field(default=Decimal("5.0000"), gt=0)
    data_quality_stale_live_seconds: int = Field(default=300, ge=1)
    intelligence_dataset_schema_version: str = "v1"
    intelligence_dataset_default_limit: int = Field(default=500, ge=1, le=5000)
    intelligence_dataset_max_limit: int = Field(default=5000, ge=1, le=50000)
    intelligence_dataset_max_text_length: int = Field(default=2000, ge=100, le=20000)
    market_session_version: str = "v1"
    market_session_default_timezone: str = "UTC"
    operator_playbook_version: str = "v1"
    operator_playbook_seed_enabled: bool = True
    engine_execution_default_max_attempts: int = Field(default=3, ge=1, le=100)
    engine_execution_lock_seconds: int = Field(default=120, ge=1)
    engine_execution_default_priority: str = "normal"
    backfill_plan_version: str = "v1"
    backfill_plan_default_limit: int = Field(default=1000, ge=1)
    backfill_plan_max_limit: int = Field(default=10000, ge=1)
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

    @field_validator("provider_polling_user_agent")
    @classmethod
    def validate_provider_polling_user_agent(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "PROVIDER_POLLING_USER_AGENT must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("candle_gap_recovery_version")
    @classmethod
    def validate_candle_gap_recovery_version(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "CANDLE_GAP_RECOVERY_VERSION must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("binance_public_rest_base_url")
    @classmethod
    def validate_binance_public_rest_base_url(cls, value: str) -> str:
        normalized_value = value.strip().rstrip("/")
        if not normalized_value.startswith(("http://", "https://")):
            msg = "BINANCE_PUBLIC_REST_BASE_URL must start with http:// or https://"
            raise ValueError(msg)
        return normalized_value

    @field_validator("llm_provider")
    @classmethod
    def normalize_llm_provider(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("llm_default_provider")
    @classmethod
    def normalize_llm_default_provider(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("scenario_ensemble_default_provider")
    @classmethod
    def normalize_scenario_ensemble_default_provider(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if not normalized_value:
            msg = "SCENARIO_ENSEMBLE_DEFAULT_PROVIDER must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("engine_execution_default_priority")
    @classmethod
    def validate_engine_execution_default_priority(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if normalized_value not in {"low", "normal", "high"}:
            msg = "ENGINE_EXECUTION_DEFAULT_PRIORITY must be low, normal, or high"
            raise ValueError(msg)
        return normalized_value

    @field_validator("artifact_graph_version")
    @classmethod
    def validate_artifact_graph_version(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "ARTIFACT_GRAPH_VERSION must not be empty"
            raise ValueError(msg)
        return normalized_value

    @model_validator(mode="after")
    def validate_backtest_experiment_limits(self) -> Self:
        if self.backtest_experiment_default_limit > self.backtest_experiment_max_limit:
            msg = "BACKTEST_EXPERIMENT_DEFAULT_LIMIT must be <= BACKTEST_EXPERIMENT_MAX_LIMIT"
            raise ValueError(msg)
        return self

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

    @field_validator("chart_ocr_provider")
    @classmethod
    def normalize_chart_ocr_provider(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if normalized_value not in {"google_vision", "mock"}:
            msg = "CHART_OCR_PROVIDER must be google_vision or mock"
            raise ValueError(msg)
        return normalized_value

    @field_validator(
        "intelligence_quality_gate_version",
        "intelligence_quality_shadow_version",
        "market_regime_version",
        "historical_case_vector_version",
        "decision_readiness_assessment_version",
        "scenario_ensemble_version",
        "scenario_outcome_evaluation_version",
        "backtest_experiment_version",
        "walk_forward_validation_version",
        "cohort_drift_version",
        "capability_registry_default_version",
        "market_memory_state_version",
    )
    @classmethod
    def validate_non_empty_version(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "Quality gate and shadow versions must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("market_session_version")
    @classmethod
    def validate_market_session_version(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "MARKET_SESSION_VERSION must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("market_session_default_timezone")
    @classmethod
    def validate_market_session_default_timezone(cls, value: str) -> str:
        normalized_value = value.strip() or "UTC"
        try:
            ZoneInfo(normalized_value)
        except ZoneInfoNotFoundError as error:
            msg = "MARKET_SESSION_DEFAULT_TIMEZONE must be a valid IANA timezone"
            raise ValueError(msg) from error
        return normalized_value

    @field_validator("notification_default_quiet_hours_timezone")
    @classmethod
    def validate_notification_default_quiet_hours_timezone(cls, value: str) -> str:
        normalized_value = value.strip() or "UTC"
        try:
            ZoneInfo(normalized_value)
        except ZoneInfoNotFoundError as error:
            msg = "NOTIFICATION_DEFAULT_QUIET_HOURS_TIMEZONE must be a valid IANA timezone"
            raise ValueError(msg) from error
        return normalized_value

    @field_validator("notification_webhook_user_agent")
    @classmethod
    def validate_notification_webhook_user_agent(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "NOTIFICATION_WEBHOOK_USER_AGENT must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("advanced_feature_pack_version")
    @classmethod
    def validate_advanced_feature_pack_version(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "ADVANCED_FEATURE_PACK_VERSION must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator(
        "rule_pack_default_key",
        "rule_pack_default_version",
        "reproducibility_manifest_version",
        "event_study_version",
        "confidence_calibration_version",
        "webhook_outbox_payload_version",
    )
    @classmethod
    def validate_non_empty_version_setting(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "Version and key settings must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("webhook_outbox_default_status")
    @classmethod
    def validate_webhook_outbox_default_status(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if normalized_value not in {"held", "pending", "cancelled"}:
            msg = "WEBHOOK_OUTBOX_DEFAULT_STATUS must be held, pending, or cancelled"
            raise ValueError(msg)
        return normalized_value

    @field_validator("outcome_default_horizons_minutes", mode="before")
    @classmethod
    def parse_outcome_default_horizons_minutes(cls, value: object) -> object:
        if isinstance(value, str):
            return [int(item.strip()) for item in value.split(",") if item.strip()]
        return value

    @field_validator("timeframe_aggregation_allowed_targets", mode="before")
    @classmethod
    def parse_timeframe_aggregation_allowed_targets(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("worker_supervisor_components", mode="before")
    @classmethod
    def parse_worker_supervisor_components(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return value

    @field_validator("outcome_default_horizons_minutes")
    @classmethod
    def validate_outcome_default_horizons_minutes(cls, value: list[int]) -> list[int]:
        normalized = sorted({horizon for horizon in value if horizon > 0})
        if not normalized:
            msg = "OUTCOME_DEFAULT_HORIZONS_MINUTES must contain at least one positive horizon"
            raise ValueError(msg)
        return normalized

    @field_validator("event_study_version")
    @classmethod
    def validate_event_study_version(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "EVENT_STUDY_VERSION must not be empty"
            raise ValueError(msg)
        return normalized_value

    @model_validator(mode="after")
    def validate_event_study_reaction_multipliers(self) -> Self:
        if (
            self.event_study_strong_reaction_multiplier
            < self.event_study_moderate_reaction_multiplier
        ):
            msg = (
                "EVENT_STUDY_STRONG_REACTION_MULTIPLIER must be greater than or equal to "
                "EVENT_STUDY_MODERATE_REACTION_MULTIPLIER"
            )
            raise ValueError(msg)
        return self

    @field_validator("outcome_evaluation_version")
    @classmethod
    def validate_outcome_evaluation_version(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "OUTCOME_EVALUATION_VERSION must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator(
        "rule_pack_default_key",
        "rule_pack_default_version",
        "reproducibility_manifest_version",
    )
    @classmethod
    def validate_reproducibility_setting(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "Rule pack and reproducibility manifest settings must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator(
        "timeframe_aggregation_version",
        "multi_timeframe_context_version",
        "cross_asset_context_version",
        "pattern_attribution_version",
    )
    @classmethod
    def validate_timeframe_aggregation_versions(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "Version settings must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("timeframe_aggregation_allowed_targets")
    @classmethod
    def validate_timeframe_aggregation_allowed_targets(cls, value: list[str]) -> list[str]:
        normalized = []
        for item in value:
            normalized_item = item.strip()
            if normalized_item and normalized_item not in normalized:
                normalized.append(normalized_item)
        if not normalized:
            msg = "TIMEFRAME_AGGREGATION_ALLOWED_TARGETS must contain at least one timeframe"
            raise ValueError(msg)
        return normalized

    @field_validator("market_regime_version")
    @classmethod
    def validate_market_regime_version(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "MARKET_REGIME_VERSION must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("historical_case_vector_version")
    @classmethod
    def validate_historical_case_vector_version(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "HISTORICAL_CASE_VECTOR_VERSION must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("data_quality_version")
    @classmethod
    def validate_data_quality_version(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "DATA_QUALITY_VERSION must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator(
        "profile_simulation_version",
        "data_quality_version",
        "intelligence_dataset_schema_version",
        "market_session_version",
        "operator_playbook_version",
        "market_session_default_timezone",
    )
    @classmethod
    def validate_non_empty_operations_value(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "Operations setting must not be empty"
            raise ValueError(msg)
        return normalized_value

    @model_validator(mode="after")
    def validate_data_quality_thresholds(self) -> Self:
        if not (
            self.data_quality_strong_threshold
            >= self.data_quality_acceptable_threshold
            >= self.data_quality_degraded_threshold
        ):
            msg = "DATA_QUALITY thresholds must be ordered strong >= acceptable >= degraded"
            raise ValueError(msg)
        return self

    @field_validator("backfill_plan_version")
    @classmethod
    def validate_backfill_plan_version(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "BACKFILL_PLAN_VERSION must not be empty"
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
        if (
            self.rate_limit_enabled
            and self.app_env in {AppEnvironment.STAGING, AppEnvironment.PRODUCTION}
            and secret_is_empty(self.redis_url)
        ):
            msg = "REDIS_URL is required for rate limiting in staging and production"
            raise ValueError(msg)
        if provider_requires_api_key(self.live_feed_provider) and secret_is_empty(
            self.live_feed_api_key
        ):
            msg = "LIVE_FEED_API_KEY is required for the selected live feed provider"
            raise ValueError(msg)
        if not (
            self.intelligence_quality_strong_threshold
            >= self.intelligence_quality_acceptable_threshold
            >= self.intelligence_quality_review_threshold
        ):
            msg = (
                "INTELLIGENCE_QUALITY_STRONG_THRESHOLD must be >= "
                "INTELLIGENCE_QUALITY_ACCEPTABLE_THRESHOLD >= "
                "INTELLIGENCE_QUALITY_REVIEW_THRESHOLD"
            )
            raise ValueError(msg)
        if self.market_regime_strong_data_quality < self.market_regime_acceptable_data_quality:
            msg = (
                "MARKET_REGIME_STRONG_DATA_QUALITY must be >= "
                "MARKET_REGIME_ACCEPTABLE_DATA_QUALITY"
            )
            raise ValueError(msg)
        if self.historical_case_default_limit > self.historical_case_max_limit:
            msg = "HISTORICAL_CASE_DEFAULT_LIMIT must be <= HISTORICAL_CASE_MAX_LIMIT"
            raise ValueError(msg)
        if self.decision_readiness_ready_threshold < self.decision_readiness_review_threshold:
            msg = (
                "DECISION_READINESS_READY_THRESHOLD must be >= "
                "DECISION_READINESS_REVIEW_THRESHOLD"
            )
            raise ValueError(msg)
        if self.app_env == AppEnvironment.PRODUCTION and not self.audit_timeline_redaction_enabled:
            msg = "AUDIT_TIMELINE_REDACTION_ENABLED must stay true in production"
            raise ValueError(msg)
        if not self.chart_unsupported_rejection_enabled:
            msg = "CHART_UNSUPPORTED_REJECTION_ENABLED must stay true"
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
