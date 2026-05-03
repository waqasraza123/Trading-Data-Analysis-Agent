from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.outcomes.schemas import normalize_horizons
from app.modules.pattern_attribution.models import (
    PatternAttributionLabel,
    PatternAttributionRunStatus,
)


class PatternAttributionFilters(ApiSchema):
    pattern_type: str | None = None
    strategy_profile_key: str | None = None
    symbol_id: UUID | None = None
    timeframe: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(default=5000, ge=1, le=50000)

    @model_validator(mode="after")
    def validate_window(self) -> "PatternAttributionFilters":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class PatternAttributionRunRequest(ApiSchema):
    workspace_id: UUID
    filters: PatternAttributionFilters = Field(default_factory=PatternAttributionFilters)
    horizons_minutes: list[int] = Field(default_factory=lambda: [15, 30, 60])
    minimum_sample_size: int | None = Field(default=None, ge=1, le=10000)

    @model_validator(mode="after")
    def validate_payload(self) -> "PatternAttributionRunRequest":
        self.horizons_minutes = normalize_horizons(self.horizons_minutes)
        return self


class PatternAttributionRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    status: PatternAttributionRunStatus
    attribution_version: str
    filters_json: dict[str, Any]
    horizons_json: list[int]
    minimum_sample_size: int
    evaluated_candidate_count: int
    evaluated_signal_count: int
    result_count: int
    summary: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class PatternAttributionResultRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    attribution_run_id: UUID
    pattern_type: str
    strategy_profile_key: str | None
    symbol_id: UUID | None
    timeframe: str | None
    horizon_minutes: int | None
    candidate_count: int
    selected_count: int
    rejected_count: int
    blocked_count: int
    average_strength_score: Decimal | None
    average_selected_confidence: Decimal | None
    continuation_count: int
    partial_follow_through_count: int
    no_follow_through_count: int
    reversal_count: int
    insufficient_data_count: int
    continuation_rate: Decimal | None
    reversal_rate: Decimal | None
    no_follow_through_rate: Decimal | None
    attribution_label: PatternAttributionLabel
    diagnostic_summary: str
    metadata_json: dict[str, Any]
    created_at: datetime
