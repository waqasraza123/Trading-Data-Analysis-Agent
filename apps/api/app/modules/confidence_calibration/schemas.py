from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.confidence_calibration.models import (
    ConfidenceCalibrationLabel,
    ConfidenceCalibrationRunStatus,
)
from app.modules.outcomes.schemas import normalize_horizons


class ConfidenceCalibrationFilters(ApiSchema):
    strategy_profile_key: str | None = None
    pattern_type: str | None = None
    symbol_id: UUID | None = None
    timeframe: str | None = None
    bias: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(default=5000, ge=1, le=50000)

    @model_validator(mode="after")
    def validate_window(self) -> "ConfidenceCalibrationFilters":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class ConfidenceCalibrationRunRequest(ApiSchema):
    workspace_id: UUID
    horizons_minutes: list[int] = Field(default_factory=lambda: [15, 30, 60])
    filters: ConfidenceCalibrationFilters = Field(default_factory=ConfidenceCalibrationFilters)
    minimum_sample_size: int | None = Field(default=None, ge=1, le=10000)
    bin_config: str | None = None

    @model_validator(mode="after")
    def validate_horizons(self) -> "ConfidenceCalibrationRunRequest":
        self.horizons_minutes = normalize_horizons(self.horizons_minutes)
        return self


class ConfidenceCalibrationRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    status: ConfidenceCalibrationRunStatus
    calibration_version: str
    filters_json: dict[str, Any]
    horizons_json: list[int]
    bin_config_json: list[dict[str, Any]]
    minimum_sample_size: int
    evaluated_signal_count: int
    evaluated_outcome_count: int
    bin_count: int
    summary: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ConfidenceCalibrationBinRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    calibration_run_id: UUID
    horizon_minutes: int
    bin_label: str
    bin_min: Decimal
    bin_max: Decimal
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
    average_confidence_score: Decimal
    confidence_alignment_score: Decimal
    calibration_label: ConfidenceCalibrationLabel
    metadata_json: dict[str, Any]
    created_at: datetime
