from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candle_gap_recovery.models import (
    CandleGapRecoveryItemStatus,
    CandleGapRecoveryMethod,
    CandleGapRecoveryPlanStatus,
)
from app.modules.candles.timeframes import Timeframe, normalize_timestamp
from app.modules.provider_polling.schemas import ProviderPollingProvider


class CandleGapRecoveryPlanCreate(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID | None = None
    timeframe: Timeframe
    start_time: datetime
    end_time: datetime

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_timestamp_to_utc(cls, value: datetime) -> datetime:
        return normalize_timestamp(value)

    @model_validator(mode="after")
    def validate_window(self) -> "CandleGapRecoveryPlanCreate":
        if self.start_time > self.end_time:
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class CandleGapRecoveryPlanRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str
    status: CandleGapRecoveryPlanStatus
    recovery_version: str
    detection_start_time: datetime
    detection_end_time: datetime
    detected_gap_count: int
    planned_request_count: int
    completed_request_count: int
    skipped_request_count: int
    failed_request_count: int
    summary: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CandleGapRecoveryItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    recovery_plan_id: UUID
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str
    gap_start_time: datetime
    gap_end_time: datetime
    expected_candle_count: int
    status: CandleGapRecoveryItemStatus
    recovery_method: CandleGapRecoveryMethod
    provider_polling_request_id: UUID | None
    skip_reason: str | None
    error_message: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CandleGapRecoveryItemListQuery(ApiSchema):
    status: CandleGapRecoveryItemStatus | None = None
    limit: int = Field(default=500, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class PrepareProviderPollingRequest(ApiSchema):
    create_requests: bool = False


class PreparedProviderPollingRequest(ApiSchema):
    recovery_item_id: UUID
    provider_polling_request_id: UUID | None = None
    status: str
    recovery_method: CandleGapRecoveryMethod
    provider: ProviderPollingProvider | None = None
    provider_symbol: str | None = None
    source_id: UUID | None = None
    timeframe: Timeframe
    start_time: datetime
    end_time: datetime
    limit: int
    expected_candle_count: int
    skip_reason: str | None = None
    error_message: str | None = None
    request_metadata_json: dict[str, Any] = Field(default_factory=dict)


class PrepareProviderPollingResponse(ApiSchema):
    plan_id: UUID
    create_requests: bool
    prepared_request_count: int
    created_request_count: int
    skipped_request_count: int
    failed_request_count: int
    requests: list[PreparedProviderPollingRequest]
