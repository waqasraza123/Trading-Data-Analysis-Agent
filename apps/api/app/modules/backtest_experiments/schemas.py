from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.backtest_experiments.models import (
    BacktestCohortLabel,
    BacktestExperimentRunStatus,
)
from app.modules.outcomes.schemas import normalize_horizons

BACKTEST_EXPERIMENT_VERSION = "v1"
DEFAULT_BACKTEST_HORIZONS_MINUTES = [15, 30, 60]
DEFAULT_BACKTEST_LIMIT = 5000
MAX_BACKTEST_LIMIT = 10000
SUPPORTED_COHORT_DIMENSIONS = {
    "strategy_profile_key",
    "pattern_type",
    "symbol_id",
    "timeframe",
    "bias",
    "classification_status",
    "confidence_label",
    "news_correlation_label",
}
OPTIONAL_COHORT_DIMENSIONS = {
    "session_label",
    "regime_label",
}
REQUESTABLE_COHORT_DIMENSIONS = SUPPORTED_COHORT_DIMENSIONS | OPTIONAL_COHORT_DIMENSIONS


class BacktestExperimentFilters(ApiSchema):
    strategy_profile_key: str | None = None
    symbol_id: UUID | None = None
    timeframe: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(default=DEFAULT_BACKTEST_LIMIT, ge=1, le=MAX_BACKTEST_LIMIT)

    @model_validator(mode="after")
    def validate_window(self) -> "BacktestExperimentFilters":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class BacktestExperimentRunRequest(ApiSchema):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    filters: BacktestExperimentFilters = Field(default_factory=BacktestExperimentFilters)
    cohort_dimensions: list[str] = Field(
        default_factory=lambda: ["strategy_profile_key", "pattern_type"]
    )
    horizons_minutes: list[int] = Field(
        default_factory=lambda: DEFAULT_BACKTEST_HORIZONS_MINUTES.copy()
    )
    minimum_sample_size: int = Field(default=20, ge=1, le=10000)

    @model_validator(mode="after")
    def validate_experiment(self) -> "BacktestExperimentRunRequest":
        self.horizons_minutes = normalize_horizons(self.horizons_minutes)
        normalized_dimensions = []
        for dimension in self.cohort_dimensions:
            normalized = dimension.strip()
            if not normalized:
                continue
            if normalized not in REQUESTABLE_COHORT_DIMENSIONS:
                msg = f"Unsupported cohort dimension: {normalized}"
                raise ValueError(msg)
            if normalized not in normalized_dimensions:
                normalized_dimensions.append(normalized)
        self.cohort_dimensions = normalized_dimensions
        return self


class BacktestExperimentRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    status: BacktestExperimentRunStatus
    experiment_version: str
    filters_json: dict[str, Any]
    cohort_dimensions_json: list[str]
    horizons_json: list[int]
    minimum_sample_size: int
    signal_count: int
    outcome_count: int
    cohort_count: int
    summary: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class BacktestExperimentCohortRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    experiment_run_id: UUID
    cohort_key: str
    cohort_dimensions_json: dict[str, Any]
    horizon_minutes: int
    sample_size: int
    evaluated_count: int
    continuation_count: int
    partial_follow_through_count: int
    no_follow_through_count: int
    reversal_count: int
    insufficient_data_count: int
    continuation_rate: Decimal
    reversal_rate: Decimal
    no_follow_through_rate: Decimal
    average_confidence_score: Decimal | None
    average_max_favorable_move: Decimal | None
    average_max_adverse_move: Decimal | None
    average_net_move: Decimal | None
    average_max_favorable_pips: Decimal | None
    average_max_adverse_pips: Decimal | None
    average_net_pips: Decimal | None
    average_max_favorable_ticks: Decimal | None
    average_max_adverse_ticks: Decimal | None
    average_net_ticks: Decimal | None
    cohort_label: BacktestCohortLabel
    summary: str
    metadata_json: dict[str, Any]
    created_at: datetime


class BacktestExperimentSummaryRead(ApiSchema):
    run: BacktestExperimentRunRead
    cohorts: list[BacktestExperimentCohortRead]
