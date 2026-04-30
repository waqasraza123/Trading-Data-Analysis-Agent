from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.action_plans.models import (
    ActionPlanCreatedFrom,
    ActionPlanSourceType,
    ActionPlanStatus,
    ReasoningActionItemStatus,
    ReasoningActionPriority,
    ReasoningActionType,
    ReasoningActionWorkerRunStatus,
)


class ActionPlanCreateRequest(ApiSchema):
    force_recompute: bool = False


class ExecuteDueActionItemsRequest(ApiSchema):
    workspace_id: UUID | None = None
    limit: int = Field(default=100, ge=1, le=500)


class ActionPlanRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    source_type: ActionPlanSourceType
    source_id: UUID
    signal_id: UUID | None
    analysis_run_id: UUID | None
    reasoning_run_id: UUID | None
    status: ActionPlanStatus
    plan_version: str
    created_from: ActionPlanCreatedFrom
    summary: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ActionItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    action_plan_id: UUID
    source_type: ActionPlanSourceType
    source_id: UUID
    signal_id: UUID | None
    analysis_run_id: UUID | None
    reasoning_run_id: UUID | None
    action_type: ReasoningActionType
    status: ReasoningActionItemStatus
    priority: ReasoningActionPriority
    due_at: datetime | None
    horizon_minutes: int | None
    idempotency_key: str
    input_json: dict[str, Any]
    result_json: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
    attempts: int
    max_attempts: int
    last_attempted_at: datetime | None
    locked_by: str | None = None
    locked_until: datetime | None = None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ActionPlanResponse(ApiSchema):
    plan: ActionPlanRead
    items: list[ActionItemRead]
    rejected_actions: list[dict[str, Any]] = Field(default_factory=list)
    skipped_actions: list[dict[str, Any]] = Field(default_factory=list)


class ActionItemExecutionRead(ApiSchema):
    item: ActionItemRead
    executed: bool
    status: ReasoningActionItemStatus
    result: dict[str, Any] | None = None


class ExecuteDueActionItemsResponse(ApiSchema):
    executed_count: int
    skipped_count: int
    failed_count: int
    items: list[ActionItemExecutionRead]


class MarkDueActionItemsResponse(ApiSchema):
    marked_count: int
    items: list[ActionItemRead]


class ReasoningActionWorkerRunRead(ApiReadSchema):
    id: UUID
    worker_id: str
    workspace_id: UUID | None
    status: ReasoningActionWorkerRunStatus
    batch_limit: int
    claimed_count: int
    completed_count: int
    skipped_count: int
    failed_count: int
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


class ReasoningActionWorkerStatusRead(ApiSchema):
    pending_count: int
    due_count: int
    running_count: int
    failed_count: int
    oldest_due_at: datetime | None
    worker_enabled: bool
    last_worker_run: ReasoningActionWorkerRunRead | None = None
