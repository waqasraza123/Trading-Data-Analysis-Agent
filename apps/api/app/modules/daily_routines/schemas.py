from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import normalize_timestamp
from app.modules.daily_routines.models import (
    DailyRoutineRunStatus,
    DailyRoutineRunStepStatus,
    DailyRoutineTemplateStatus,
    DailyRoutineType,
)


class DailyRoutineStepDefinition(ApiSchema):
    step_key: str = Field(min_length=1, max_length=64)
    required: bool = False
    input_json: dict[str, Any] = Field(default_factory=dict)


class DailyRoutineTemplateRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    key: str
    name: str
    description: str
    status: DailyRoutineTemplateStatus
    routine_version: str
    routine_type: DailyRoutineType
    steps_json: list[dict[str, Any]]
    default_filters_json: dict[str, Any]
    schedule_hint_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DailyRoutineRunRequest(ApiSchema):
    workspace_id: UUID
    input_json: dict[str, Any] = Field(default_factory=dict)
    enable_notifications: bool = False
    force: bool = False
    allow_provider_polling: bool = False
    watchlist_id: UUID | None = None
    preference_profile_id: UUID | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None

    @model_validator(mode="after")
    def validate_period(self) -> "DailyRoutineRunRequest":
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
        return self


class DailyRoutineTemplateListFilters(ApiSchema):
    workspace_id: UUID | None = None
    routine_type: DailyRoutineType | None = None
    status: DailyRoutineTemplateStatus = DailyRoutineTemplateStatus.ACTIVE


class DailyRoutineRunListFilters(ApiSchema):
    workspace_id: UUID
    template_id: UUID | None = None
    status: DailyRoutineRunStatus | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class DailyRoutineRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    template_id: UUID
    status: DailyRoutineRunStatus
    routine_version: str
    input_json: dict[str, Any]
    step_results_json: list[dict[str, Any]]
    created_artifact_ids_json: dict[str, Any]
    summary: str
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DailyRoutineRunStepRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    routine_run_id: UUID
    step_key: str
    status: DailyRoutineRunStepStatus
    input_json: dict[str, Any]
    output_json: dict[str, Any] | None
    skipped_reason: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DailyRoutineSeedRead(ApiSchema):
    seeded_count: int
    templates: list[DailyRoutineTemplateRead]


class DailyRoutineNotificationOptions(ApiSchema):
    enabled: bool = False
    severity: str = "info"

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"info", "low", "medium", "high", "critical"}:
            msg = "severity must be info, low, medium, high, or critical"
            raise ValueError(msg)
        return normalized
