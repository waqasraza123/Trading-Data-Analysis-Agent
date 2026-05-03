from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.data_quality.models import DataQualityLabel, DataQualityRunStatus, DataQualityScopeType


class DataQualityCandleRangeRequest(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID | None = None
    timeframe: str
    start_time: datetime | None = None
    end_time: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self) -> "DataQualityCandleRangeRequest":
        if self.start_time is not None and self.end_time is not None and self.start_time > self.end_time:
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class DataQualitySourceRunRequest(ApiSchema):
    workspace_id: UUID


class DataQualityRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    scope_type: DataQualityScopeType
    status: DataQualityRunStatus
    quality_version: str
    symbol_id: UUID | None
    source_id: UUID | None
    live_subscription_id: UUID | None
    timeframe: str | None
    start_time: datetime | None
    end_time: datetime | None
    candle_count: int
    finding_count: int
    quality_score: Decimal
    quality_label: DataQualityLabel
    summary_json: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DataQualityFindingRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    data_quality_run_id: UUID
    finding_type: str
    severity: str
    message: str
    metadata_json: dict[str, Any]
    created_at: datetime
