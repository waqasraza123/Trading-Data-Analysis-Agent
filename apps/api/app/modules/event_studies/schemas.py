from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.event_studies.models import (
    EventStudyDataQualityLabel,
    EventStudyDirectionLabel,
    EventStudyReactionLabel,
    EventStudyRunStatus,
    EventStudyVolatilityReaction,
)


class EventStudyRunRequest(ApiSchema):
    workspace_id: UUID
    news_event_id: UUID
    timeframes: list[str] = Field(min_length=1, max_length=24)
    symbol_ids: list[UUID] = Field(default_factory=list, max_length=500)
    pre_event_minutes: int | None = Field(default=None, ge=0, le=10080)
    post_event_minutes: int | None = Field(default=None, ge=1, le=10080)

    @field_validator("timeframes")
    @classmethod
    def normalize_timeframes(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if not normalized:
            msg = "At least one timeframe is required"
            raise ValueError(msg)
        unique_values = list(dict.fromkeys(normalized))
        return unique_values

    @field_validator("symbol_ids")
    @classmethod
    def deduplicate_symbol_ids(cls, value: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def validate_window(self) -> "EventStudyRunRequest":
        if (
            self.pre_event_minutes is not None
            and self.post_event_minutes is not None
            and self.pre_event_minutes == 0
            and self.post_event_minutes == 0
        ):
            msg = "At least one event window must be positive"
            raise ValueError(msg)
        return self


class EventStudyRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    news_event_id: UUID
    status: EventStudyRunStatus
    event_study_version: str
    pre_event_minutes: int
    post_event_minutes: int
    symbol_filters_json: dict[str, Any]
    analyzed_symbol_count: int
    result_count: int
    summary: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class EventStudyResultRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    event_study_run_id: UUID
    news_event_id: UUID
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str
    event_time: datetime
    pre_window_start: datetime
    pre_window_end: datetime
    post_window_start: datetime
    post_window_end: datetime
    pre_candle_count: int
    post_candle_count: int
    pre_move: Decimal
    post_move: Decimal
    post_move_pips: Decimal | None
    post_move_ticks: Decimal | None
    pre_volatility_json: dict[str, Any]
    post_volatility_json: dict[str, Any]
    volatility_reaction: EventStudyVolatilityReaction
    direction_label: EventStudyDirectionLabel
    reaction_label: EventStudyReactionLabel
    data_quality_label: EventStudyDataQualityLabel
    metadata_json: dict[str, Any]
    created_at: datetime
