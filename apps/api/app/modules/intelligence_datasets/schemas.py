from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.intelligence_datasets.models import (
    IntelligenceDatasetExportFormat,
    IntelligenceDatasetExportStatus,
)


class IntelligenceDatasetExportFilters(ApiSchema):
    symbol_id: UUID | None = None
    timeframe: str | None = None
    strategy_profile_key: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self) -> "IntelligenceDatasetExportFilters":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class IntelligenceDatasetExportCreate(ApiSchema):
    workspace_id: UUID
    filters: IntelligenceDatasetExportFilters = Field(
        default_factory=IntelligenceDatasetExportFilters
    )
    limit: int | None = None
    include_outcomes: bool = True
    include_market_session: bool = True
    include_data_quality_label: bool = True


class IntelligenceDatasetExportRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    status: IntelligenceDatasetExportStatus
    export_format: IntelligenceDatasetExportFormat
    schema_version: str
    filters_json: dict[str, Any]
    redaction_policy_json: dict[str, Any]
    requested_limit: int
    item_count: int
    summary_json: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class IntelligenceDatasetExportItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    export_id: UUID
    sequence_number: int
    signal_id: UUID | None
    analysis_run_id: UUID | None
    item_json: dict[str, Any]
    redaction_json: dict[str, Any]
    created_at: datetime
