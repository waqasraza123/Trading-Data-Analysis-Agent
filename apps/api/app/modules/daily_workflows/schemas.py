from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import normalize_timestamp
from app.modules.daily_workflows.models import (
    DailyWorkflowRunStatus,
    DailyWorkflowStepKey,
    DailyWorkflowStepStatus,
    DailyWorkflowType,
)


class DailyWorkflowOptions(ApiSchema):
    prepare_gap_recovery: bool = True
    allow_provider_polling: bool = False
    run_scan: bool = True
    generate_setup_context: bool = True
    score_priorities: bool = True
    generate_digest: bool = True
    generate_brief: bool = True
    force: bool = False


class DailyWorkflowRunRequest(ApiSchema):
    workspace_id: UUID
    workflow_type: DailyWorkflowType = DailyWorkflowType.DAILY_SCAN
    watchlist_id: UUID | None = None
    preference_profile_id: UUID | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    options: DailyWorkflowOptions = Field(default_factory=DailyWorkflowOptions)
    filters_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_request(self) -> "DailyWorkflowRunRequest":
        if self.period_start is not None:
            self.period_start = normalize_timestamp(self.period_start)
        if self.period_end is not None:
            self.period_end = normalize_timestamp(self.period_end)
        if (
            self.period_start is not None
            and self.period_end is not None
            and self.period_start >= self.period_end
        ):
            msg = "period_start must be before period_end"
            raise ValueError(msg)
        if self.workflow_type == DailyWorkflowType.WATCHLIST_SCAN and self.watchlist_id is None:
            msg = "watchlist_id is required for watchlist_scan"
            raise ValueError(msg)
        return self


class DailyWorkflowRunListFilters(ApiSchema):
    workspace_id: UUID
    workflow_type: DailyWorkflowType | None = None
    status: DailyWorkflowRunStatus | None = None
    watchlist_id: UUID | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class DailyWorkflowRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    workflow_type: DailyWorkflowType
    status: DailyWorkflowRunStatus
    workflow_version: str
    watchlist_id: UUID | None
    preference_profile_id: UUID | None
    period_start: datetime | None
    period_end: datetime | None
    filters_json: dict[str, Any]
    steps_json: list[dict[str, Any]]
    result_json: dict[str, Any]
    created_artifact_ids_json: dict[str, Any]
    summary: str
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DailyWorkflowStepRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    workflow_run_id: UUID
    step_key: DailyWorkflowStepKey
    status: DailyWorkflowStepStatus
    started_at: datetime | None
    completed_at: datetime | None
    input_json: dict[str, Any]
    output_json: dict[str, Any] | None
    skipped_reason: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
