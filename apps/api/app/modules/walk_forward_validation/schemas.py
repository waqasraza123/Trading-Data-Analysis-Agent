from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.outcomes.schemas import normalize_horizons
from app.modules.walk_forward_validation.models import (
    WalkForwardStabilityLabel,
    WalkForwardValidationRunStatus,
)

DEFAULT_WALK_FORWARD_HORIZONS_MINUTES = [15, 30, 60]
DEFAULT_WALK_FORWARD_MAX_SIGNALS = 5000
MAX_WALK_FORWARD_MAX_SIGNALS = 10000


class WalkForwardValidationFilters(ApiSchema):
    strategy_profile_key: str | None = None
    pattern_type: str | None = None
    symbol_id: UUID | None = None
    timeframe: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    max_signals: int = Field(
        default=DEFAULT_WALK_FORWARD_MAX_SIGNALS,
        ge=1,
        le=MAX_WALK_FORWARD_MAX_SIGNALS,
    )

    @model_validator(mode="after")
    def validate_time_window(self) -> "WalkForwardValidationFilters":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class WalkForwardValidationRunRequest(ApiSchema):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=160)
    filters: WalkForwardValidationFilters = Field(default_factory=WalkForwardValidationFilters)
    window_days: int | None = Field(default=None, ge=1, le=3660)
    horizons_minutes: list[int] = Field(
        default_factory=lambda: DEFAULT_WALK_FORWARD_HORIZONS_MINUTES.copy()
    )
    minimum_sample_size: int | None = Field(default=None, ge=1, le=10000)

    @model_validator(mode="after")
    def validate_horizons(self) -> "WalkForwardValidationRunRequest":
        self.horizons_minutes = normalize_horizons(self.horizons_minutes)
        return self


class WalkForwardValidationRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    name: str
    status: WalkForwardValidationRunStatus
    validation_version: str
    filters_json: dict[str, Any]
    window_config_json: dict[str, Any]
    horizons_json: list[int]
    minimum_sample_size: int
    window_count: int
    evaluated_signal_count: int
    evaluated_outcome_count: int
    summary: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class WalkForwardValidationWindowRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    validation_run_id: UUID
    window_index: int
    window_start: datetime
    window_end: datetime
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
    confidence_alignment_score: Decimal | None
    stability_label: WalkForwardStabilityLabel
    summary: str
    metadata_json: dict[str, Any]
    created_at: datetime


class WalkForwardValidationComparisonRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    validation_run_id: UUID
    horizon_minutes: int
    compared_window_count: int
    stability_score: Decimal
    degradation_detected: bool
    improvement_detected: bool
    summary: str
    metadata_json: dict[str, Any]
    created_at: datetime
