from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import Timeframe
from app.modules.timeframe_aggregation.models import (
    CandleAggregationRunStatus,
    TimeframeAgreementLabel,
    TimeframeAlignment,
)


class TimeframeAggregationRunCreate(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID | None = None
    base_timeframe: Timeframe
    target_timeframe: Timeframe
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def validate_window(self) -> "TimeframeAggregationRunCreate":
        if self.start_time > self.end_time:
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class CandleAggregationRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID | None
    base_timeframe: str
    target_timeframe: str
    start_time: datetime
    end_time: datetime
    status: CandleAggregationRunStatus
    expected_base_candle_count: int
    available_base_candle_count: int
    produced_candle_count: int
    skipped_candle_count: int
    incomplete_window_count: int
    aggregation_version: str
    summary: str
    metadata_json: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DerivedCandleLineageRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    aggregation_run_id: UUID
    derived_candle_id: UUID
    symbol_id: UUID
    source_id: UUID | None
    base_timeframe: str
    target_timeframe: str
    derived_timestamp: datetime
    base_start_time: datetime
    base_end_time: datetime
    expected_base_count: int
    actual_base_count: int
    completeness_score: Decimal
    is_complete: bool
    metadata_json: dict[str, Any]
    created_at: datetime


class MultiTimeframeContextCreate(ApiSchema):
    context_timeframes: list[Timeframe] = Field(default_factory=list)
    force_recompute: bool = False

    @field_validator("context_timeframes")
    @classmethod
    def dedupe_timeframes(cls, value: list[Timeframe]) -> list[Timeframe]:
        seen: set[Timeframe] = set()
        result: list[Timeframe] = []
        for timeframe in value:
            if timeframe not in seen:
                seen.add(timeframe)
                result.append(timeframe)
        return result


class MultiTimeframeContextRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    analysis_run_id: UUID | None
    signal_id: UUID | None
    symbol_id: UUID
    source_id: UUID | None
    primary_timeframe: str
    context_timeframes_json: list[str]
    context_version: str
    trend_alignment: TimeframeAlignment
    volatility_alignment: TimeframeAlignment
    range_alignment: TimeframeAlignment
    agreement_score: Decimal
    agreement_label: TimeframeAgreementLabel
    context_summary: str
    context_json: dict[str, Any]
    warnings_json: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
