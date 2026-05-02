from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.operator_reviews.models import (
    OperatorReviewEventType,
    OperatorReviewPriority,
    OperatorReviewResolution,
    OperatorReviewSourceType,
    OperatorReviewStatus,
    OperatorReviewType,
)


class OperatorReviewCreateRequest(ApiSchema):
    workspace_id: UUID
    source_type: OperatorReviewSourceType
    source_id: UUID
    review_type: OperatorReviewType
    priority: OperatorReviewPriority = OperatorReviewPriority.NORMAL
    title: str = Field(min_length=1, max_length=240)
    summary: str = Field(min_length=1)
    reason_code: str | None = Field(default=None, max_length=80)
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    related_analysis_run_id: UUID | None = None
    related_signal_id: UUID | None = None
    related_reasoning_run_id: UUID | None = None
    related_action_item_id: UUID | None = None
    assigned_to_user_id: UUID | None = None
    created_by_user_id: UUID | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    force_create: bool = False


class OperatorReviewAssignRequest(ApiSchema):
    user_id: UUID
    actor_user_id: UUID | None = None


class OperatorReviewStatusUpdateRequest(ApiSchema):
    status: OperatorReviewStatus
    actor_user_id: UUID | None = None
    notes: str | None = None


class OperatorReviewResolveRequest(ApiSchema):
    resolution: OperatorReviewResolution
    resolution_notes: str | None = None
    reviewed_by_user_id: UUID | None = None


class OperatorReviewDismissRequest(ApiSchema):
    resolution_notes: str | None = None
    reviewed_by_user_id: UUID | None = None


class OperatorReviewItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    source_type: OperatorReviewSourceType
    source_id: UUID
    related_analysis_run_id: UUID | None
    related_signal_id: UUID | None
    related_reasoning_run_id: UUID | None
    related_action_item_id: UUID | None
    review_type: OperatorReviewType
    priority: OperatorReviewPriority
    status: OperatorReviewStatus
    title: str
    summary: str
    reason_code: str | None
    evidence_json: dict[str, Any]
    assigned_to_user_id: UUID | None
    resolution: OperatorReviewResolution | None
    resolution_notes: str | None
    created_by_user_id: UUID | None
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class OperatorReviewEventRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    review_item_id: UUID
    event_type: OperatorReviewEventType
    user_id: UUID | None
    message: str
    metadata_json: dict[str, Any]
    created_at: datetime
