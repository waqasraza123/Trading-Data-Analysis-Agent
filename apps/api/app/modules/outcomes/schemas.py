from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.outcomes.models import (
    OutcomeEvaluationRunStatus,
    OutcomeEvaluationScopeType,
    OutcomeEvaluationStatus,
    OutcomeLabel,
)


DEFAULT_OUTCOME_HORIZONS_MINUTES = [5, 15, 30, 60]


class OutcomeEvaluationRequest(ApiSchema):
    horizons_minutes: list[int] = Field(default_factory=lambda: DEFAULT_OUTCOME_HORIZONS_MINUTES.copy())
    force_recompute: bool = False

    @model_validator(mode="after")
    def validate_horizons(self) -> "OutcomeEvaluationRequest":
        self.horizons_minutes = normalize_horizons(self.horizons_minutes)
        return self


class OutcomeBackfillRequest(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID | None = None
    timeframe: str | None = None
    horizons_minutes: list[int] = Field(default_factory=lambda: DEFAULT_OUTCOME_HORIZONS_MINUTES.copy())
    force_recompute: bool = False
    limit: int = Field(default=500, ge=1, le=5000)
    include_replay: bool = False

    @model_validator(mode="after")
    def validate_horizons(self) -> "OutcomeBackfillRequest":
        self.horizons_minutes = normalize_horizons(self.horizons_minutes)
        return self


class OutcomePerformanceQuery(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID | None = None
    timeframe: str | None = None
    horizon_minutes: int = Field(gt=0)
    pattern_type: str | None = None
    strategy_profile_key: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self) -> "OutcomePerformanceQuery":
        if self.start_time is not None and self.end_time is not None and self.start_time > self.end_time:
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class SignalOutcomeRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    analysis_run_id: UUID
    signal_id: UUID
    symbol_id: UUID
    timeframe: str
    strategy_profile_key: str | None
    strategy_profile_version: str | None
    pattern_type: str | None
    bias: str
    classification_status: str
    horizon_minutes: int
    evaluation_status: OutcomeEvaluationStatus
    reference_time: datetime
    reference_price: Decimal | None
    future_window_start: datetime
    future_window_end: datetime
    future_candle_count: int
    max_favorable_move: Decimal
    max_adverse_move: Decimal
    net_move: Decimal
    max_favorable_pips: Decimal | None
    max_adverse_pips: Decimal | None
    net_pips: Decimal | None
    max_favorable_ticks: Decimal | None
    max_adverse_ticks: Decimal | None
    net_ticks: Decimal | None
    direction_followed: bool | None
    reversal_detected: bool
    outcome_label: OutcomeLabel
    movement_quality: str | None
    evaluation_version: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SignalOutcomeEvaluationRead(ApiSchema):
    signal_id: UUID
    outcomes: list[SignalOutcomeRead]


class AnalysisRunOutcomeEvaluationRead(ApiSchema):
    analysis_run_id: UUID
    outcomes: list[SignalOutcomeRead]


class OutcomeEvaluationRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    status: OutcomeEvaluationRunStatus
    scope_type: OutcomeEvaluationScopeType
    horizons_json: list[int]
    filters_json: dict[str, Any]
    evaluated_count: int
    skipped_count: int
    failed_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OutcomePerformanceRead(ApiSchema):
    group_key: str
    pattern_type: str | None = None
    strategy_profile_key: str | None = None
    symbol_id: UUID | None = None
    timeframe: str | None = None
    horizon_minutes: int
    evaluated_count: int
    continuation_count: int
    partial_follow_through_count: int
    reversal_count: int
    no_follow_through_count: int
    insufficient_data_count: int
    continuation_rate: Decimal
    reversal_rate: Decimal
    historical_follow_through_rate: Decimal
    average_max_favorable_move: Decimal | None
    average_max_adverse_move: Decimal | None
    average_net_move: Decimal | None
    average_max_favorable_pips: Decimal | None
    average_max_adverse_pips: Decimal | None
    average_net_pips: Decimal | None
    average_max_favorable_ticks: Decimal | None
    average_max_adverse_ticks: Decimal | None
    average_net_ticks: Decimal | None


def normalize_horizons(horizons: list[int]) -> list[int]:
    normalized = sorted({horizon for horizon in horizons if horizon > 0})
    if not normalized:
        msg = "At least one positive horizon is required"
        raise ValueError(msg)
    return normalized
