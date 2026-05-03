from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.cohort_drift.models import (
    CohortDriftLabel,
    CohortDriftRunStatus,
    CohortDriftSeverity,
)
from app.modules.outcomes.schemas import normalize_horizons

DEFAULT_COHORT_DRIFT_HORIZONS_MINUTES = [15, 30, 60]
DEFAULT_COHORT_DRIFT_COHORT_DIMENSIONS = [
    "strategy_profile_key",
    "pattern_type",
    "symbol_id",
]
DEFAULT_COHORT_DRIFT_MAX_OUTCOMES = 10000
MAX_COHORT_DRIFT_MAX_OUTCOMES = 50000
SUPPORTED_COHORT_DRIFT_DIMENSIONS = {
    "strategy_profile_key",
    "pattern_type",
    "symbol_id",
    "timeframe",
    "bias",
    "confidence_label",
    "market_session_label",
    "market_regime_label",
}


class CohortDriftFilters(ApiSchema):
    strategy_profile_key: str | None = None
    symbol_id: UUID | None = None
    timeframe: str | None = None
    pattern_type: str | None = None
    bias: str | None = None
    confidence_label: str | None = None
    max_outcomes: int = Field(
        default=DEFAULT_COHORT_DRIFT_MAX_OUTCOMES,
        ge=1,
        le=MAX_COHORT_DRIFT_MAX_OUTCOMES,
    )


class CohortDriftWindow(ApiSchema):
    start_time: datetime | None = None
    end_time: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self) -> "CohortDriftWindow":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time >= self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class CohortDriftRunRequest(ApiSchema):
    workspace_id: UUID
    filters: CohortDriftFilters = Field(default_factory=CohortDriftFilters)
    baseline_window: CohortDriftWindow | None = None
    comparison_window: CohortDriftWindow | None = None
    cohort_dimensions: list[str] = Field(
        default_factory=lambda: DEFAULT_COHORT_DRIFT_COHORT_DIMENSIONS.copy()
    )
    horizons_minutes: list[int] = Field(
        default_factory=lambda: DEFAULT_COHORT_DRIFT_HORIZONS_MINUTES.copy()
    )
    minimum_sample_size: int | None = Field(default=None, ge=1, le=10000)

    @model_validator(mode="after")
    def validate_request(self) -> "CohortDriftRunRequest":
        self.horizons_minutes = normalize_horizons(self.horizons_minutes)
        normalized_dimensions: list[str] = []
        for dimension in self.cohort_dimensions:
            normalized = dimension.strip()
            if not normalized:
                continue
            if normalized not in SUPPORTED_COHORT_DRIFT_DIMENSIONS:
                msg = f"Unsupported cohort dimension: {normalized}"
                raise ValueError(msg)
            if normalized not in normalized_dimensions:
                normalized_dimensions.append(normalized)
        if not normalized_dimensions:
            msg = "At least one cohort dimension is required"
            raise ValueError(msg)
        self.cohort_dimensions = normalized_dimensions
        if (
            self.baseline_window is not None
            and self.comparison_window is not None
            and self.baseline_window.end_time is not None
            and self.comparison_window.start_time is not None
            and self.baseline_window.end_time > self.comparison_window.start_time
        ):
            msg = "baseline_window end_time must be before or equal to comparison_window start_time"
            raise ValueError(msg)
        return self


class CohortDriftRecentResultsFilters(ApiSchema):
    workspace_id: UUID
    drift_label: CohortDriftLabel | None = None
    severity: CohortDriftSeverity | None = None
    cohort_key: str | None = None
    horizon_minutes: int | None = Field(default=None, gt=0)
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class CohortDriftRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    status: CohortDriftRunStatus
    drift_version: str
    filters_json: dict[str, Any]
    baseline_window_json: dict[str, Any]
    comparison_window_json: dict[str, Any]
    cohort_dimensions_json: list[str]
    horizons_json: list[int]
    minimum_sample_size: int
    cohort_count: int
    drift_detected_count: int
    summary: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class CohortDriftResultRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    drift_run_id: UUID
    cohort_key: str
    cohort_dimensions_json: dict[str, Any]
    horizon_minutes: int
    baseline_sample_size: int
    comparison_sample_size: int
    baseline_continuation_rate: Decimal | None
    comparison_continuation_rate: Decimal | None
    continuation_rate_delta: Decimal | None
    baseline_reversal_rate: Decimal | None
    comparison_reversal_rate: Decimal | None
    reversal_rate_delta: Decimal | None
    baseline_no_follow_through_rate: Decimal | None
    comparison_no_follow_through_rate: Decimal | None
    no_follow_through_delta: Decimal | None
    baseline_confidence_alignment: Decimal | None
    comparison_confidence_alignment: Decimal | None
    confidence_alignment_delta: Decimal | None
    drift_score: Decimal
    drift_label: CohortDriftLabel
    severity: CohortDriftSeverity
    summary: str
    metadata_json: dict[str, Any]
    created_at: datetime
