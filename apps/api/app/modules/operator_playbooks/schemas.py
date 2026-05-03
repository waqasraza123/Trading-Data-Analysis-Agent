from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.operator_playbooks.models import (
    OperatorPlaybookEvaluationStatus,
    OperatorPlaybookRecommendationType,
)


class OperatorPlaybookRead(ApiReadSchema):
    id: UUID
    key: str
    version: str
    name: str
    description: str
    is_enabled: bool
    priority: int
    rules_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class OperatorPlaybookEvaluationRequest(ApiSchema):
    workspace_id: UUID
    subject_type: str = Field(default="workspace")
    subject_id: UUID | None = None
    input_json: dict[str, Any] = Field(default_factory=dict)


class OperatorPlaybookEvaluationRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    playbook_id: UUID | None
    status: OperatorPlaybookEvaluationStatus
    recommendation_type: OperatorPlaybookRecommendationType
    subject_type: str
    subject_id: UUID | None
    rationale: str
    input_json: dict[str, Any]
    result_json: dict[str, Any]
    created_at: datetime
