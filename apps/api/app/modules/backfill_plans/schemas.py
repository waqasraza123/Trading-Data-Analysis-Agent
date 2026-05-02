from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.backfill_plans.models import (
    BackfillItemPriority,
    BackfillItemStatus,
    BackfillItemTargetType,
    BackfillPlanStatus,
    BackfillPlanType,
)


SUPPORTED_BACKFILL_OPERATIONS = {
    "outcomes.evaluate",
    "market_regime.generate",
    "market_session.generate",
    "advanced_features.generate",
    "historical_case_vector.generate",
    "reproducibility_manifest.generate",
    "decision_readiness.assess",
    "intelligence_quality.run",
    "data_quality.run",
    "confidence_calibration.run",
}


class BackfillPlanFilters(ApiSchema):
    symbol_id: UUID | None = None
    timeframe: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int | None = Field(default=None, ge=1)
    horizons_minutes: list[int] | None = None
    include_replay: bool = False

    @model_validator(mode="after")
    def validate_window(self) -> "BackfillPlanFilters":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        if self.horizons_minutes is not None:
            normalized = sorted({horizon for horizon in self.horizons_minutes if horizon > 0})
            if not normalized:
                msg = "horizons_minutes must contain at least one positive value"
                raise ValueError(msg)
            self.horizons_minutes = normalized
        return self


class BackfillPlanCreate(ApiSchema):
    workspace_id: UUID
    plan_type: BackfillPlanType
    target_module: str | None = None
    target_operation: str | None = None
    filters: BackfillPlanFilters = Field(default_factory=BackfillPlanFilters)
    dry_run: bool = True
    create_execution_records: bool = False

    @model_validator(mode="after")
    def validate_operation(self) -> "BackfillPlanCreate":
        if self.target_operation is not None and self.target_operation not in SUPPORTED_BACKFILL_OPERATIONS:
            msg = "Unsupported backfill target operation"
            raise ValueError(msg)
        return self


class BackfillPlanRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    plan_type: BackfillPlanType
    status: BackfillPlanStatus
    plan_version: str
    filters_json: dict[str, Any]
    target_module: str
    target_operation: str
    dry_run: bool
    eligible_count: int
    planned_count: int
    skipped_count: int
    blocked_count: int
    summary: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class BackfillItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    backfill_plan_id: UUID
    target_type: BackfillItemTargetType
    target_id: UUID
    target_operation: str
    status: BackfillItemStatus
    priority: BackfillItemPriority
    idempotency_key: str
    input_json: dict[str, Any]
    skip_reason: str | None
    block_reason: str | None
    execution_record_id: UUID | None
    result_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class BackfillPlanListQuery(ApiSchema):
    workspace_id: UUID
    plan_type: BackfillPlanType | None = None
    status: BackfillPlanStatus | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class BackfillItemListQuery(ApiSchema):
    status: BackfillItemStatus | None = None
    limit: int = Field(default=500, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
