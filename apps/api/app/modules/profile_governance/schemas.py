from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.profile_governance.models import (
    StrategyProfileDraftEventType,
    StrategyProfileDraftStatus,
    StrategyProfileDraftValidationStatus,
)


class StrategyProfileDraftCreate(ApiSchema):
    workspace_id: UUID
    base_strategy_profile_id: UUID | None = None
    base_strategy_profile_key: str = Field(min_length=1, max_length=80)
    base_strategy_profile_version: str | None = Field(default=None, max_length=32)
    draft_key: str = Field(min_length=1, max_length=80)
    draft_version: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1000)
    proposed_config_json: dict[str, Any]
    simulation_run_id: UUID | None = None
    diagnostic_run_id: UUID | None = None
    created_by_user_id: UUID | None = None


class StrategyProfileDraftUpdate(ApiSchema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, min_length=1, max_length=1000)
    proposed_config_json: dict[str, Any] | None = None
    simulation_run_id: UUID | None = None
    diagnostic_run_id: UUID | None = None
    review_notes: str | None = Field(default=None, max_length=4000)
    user_id: UUID | None = None


class StrategyProfileDraftWorkflowRequest(ApiSchema):
    user_id: UUID | None = None
    review_notes: str | None = Field(default=None, max_length=4000)


class StrategyProfileDraftPromotionRequest(ApiSchema):
    user_id: UUID | None = None
    deactivate_previous: bool = False
    review_notes: str | None = Field(default=None, max_length=4000)


class StrategyProfileDraftRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    base_strategy_profile_id: UUID | None
    base_strategy_profile_key: str
    base_strategy_profile_version: str | None
    draft_key: str
    draft_version: str
    status: StrategyProfileDraftStatus
    name: str
    description: str
    proposed_config_json: dict[str, Any]
    validation_status: StrategyProfileDraftValidationStatus
    validation_errors_json: list[dict[str, Any]]
    validation_warnings_json: list[dict[str, Any]]
    diff_json: dict[str, Any]
    simulation_run_id: UUID | None
    diagnostic_run_id: UUID | None
    created_by_user_id: UUID | None
    reviewed_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    rejected_by_user_id: UUID | None
    promoted_strategy_profile_id: UUID | None
    review_notes: str | None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    promoted_at: datetime | None


class StrategyProfileDraftEventRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    draft_id: UUID
    event_type: StrategyProfileDraftEventType
    user_id: UUID | None
    message: str
    metadata_json: dict[str, Any]
    created_at: datetime
