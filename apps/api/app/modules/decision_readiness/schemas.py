from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.decision_readiness.models import (
    DecisionReadinessLabel,
    DecisionReadinessSourceType,
    DecisionReadinessStatus,
)


class DecisionReadinessAssessmentRequest(ApiSchema):
    force_recompute: bool = False


class DecisionReadinessAssessmentRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    source_type: DecisionReadinessSourceType
    source_id: UUID
    analysis_run_id: UUID | None
    signal_id: UUID | None
    assessment_version: str
    readiness_score: float
    readiness_label: DecisionReadinessLabel
    status: DecisionReadinessStatus
    required_checks_json: list[dict[str, object]]
    optional_checks_json: list[dict[str, object]]
    blockers_json: list[dict[str, object]]
    warnings_json: list[dict[str, object]]
    next_steps_json: list[str]
    summary: str
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class DecisionReadinessAssessmentSummary(ApiSchema):
    readiness_score: float
    readiness_label: DecisionReadinessLabel
    summary: str


class DecisionReadinessAssessmentResponse(ApiSchema):
    assessment: DecisionReadinessAssessmentSummary
    blockers: list[dict[str, object]] = Field(default_factory=list)
    warnings: list[dict[str, object]] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class DecisionReadinessAssessmentListResponse(ApiSchema):
    assessments: list[DecisionReadinessAssessmentRead]
