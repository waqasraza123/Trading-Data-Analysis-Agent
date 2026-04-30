from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.outcomes.schemas import normalize_horizons
from app.modules.profile_diagnostics.models import (
    CalibrationRecommendationSeverity,
    CalibrationRecommendationStatus,
    CalibrationRecommendationType,
    DiagnosticLabel,
    DiagnosticRunStatus,
    DiagnosticScopeType,
)


class ProfileDiagnosticRunRequest(ApiSchema):
    workspace_id: UUID
    strategy_profile_key: str | None = None
    symbol_id: UUID | None = None
    timeframe: str | None = None
    pattern_type: str | None = None
    horizons_minutes: list[int] = Field(default_factory=lambda: [15, 30, 60])
    minimum_sample_size: int | None = Field(default=None, ge=1, le=10000)
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int = Field(default=5000, ge=1, le=50000)

    @model_validator(mode="after")
    def validate_payload(self) -> "ProfileDiagnosticRunRequest":
        self.horizons_minutes = normalize_horizons(self.horizons_minutes)
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class StrategyProfileDiagnosticRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    status: DiagnosticRunStatus
    scope_type: DiagnosticScopeType
    filters_json: dict[str, Any]
    horizons_json: list[int]
    minimum_sample_size: int
    evaluated_signal_count: int
    evaluated_outcome_count: int
    diagnostics_created_count: int
    recommendations_created_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StrategyProfileDiagnosticRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    diagnostic_run_id: UUID
    strategy_profile_key: str
    strategy_profile_version: str | None
    symbol_id: UUID | None
    timeframe: str | None
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
    confidence_alignment_score: Decimal | None
    diagnostic_label: DiagnosticLabel
    diagnostic_summary: str
    metadata_json: dict[str, Any]
    created_at: datetime


class PatternOutcomeDiagnosticRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    diagnostic_run_id: UUID
    pattern_type: str
    strategy_profile_key: str | None
    symbol_id: UUID | None
    timeframe: str | None
    horizon_minutes: int
    sample_size: int
    evaluated_count: int
    continuation_rate: Decimal
    reversal_rate: Decimal
    no_follow_through_rate: Decimal
    average_confidence_score: Decimal | None
    confidence_alignment_score: Decimal | None
    diagnostic_label: DiagnosticLabel
    diagnostic_summary: str
    metadata_json: dict[str, Any]
    created_at: datetime


class CalibrationRecommendationRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    diagnostic_run_id: UUID
    recommendation_type: CalibrationRecommendationType
    strategy_profile_key: str | None
    strategy_profile_version: str | None
    pattern_type: str | None
    symbol_id: UUID | None
    timeframe: str | None
    horizon_minutes: int | None
    severity: CalibrationRecommendationSeverity
    status: CalibrationRecommendationStatus
    title: str
    rationale: str
    suggested_change_json: dict[str, Any]
    evidence_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CalibrationRecommendationStatusUpdate(ApiSchema):
    status: CalibrationRecommendationStatus
