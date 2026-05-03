from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.explanation_comparison.models import (
    ExplanationAlignmentLabel,
    ExplanationComparisonFindingType,
    ExplanationComparisonRunStatus,
    ExplanationComparisonSeverity,
)


class ExplanationComparisonRequest(ApiSchema):
    force_recompute: bool = False


class ExplanationComparisonRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    signal_id: UUID
    analysis_run_id: UUID | None
    status: ExplanationComparisonRunStatus
    comparison_version: str
    deterministic_explanation_id: UUID | None
    llm_explanation_id: UUID | None
    reasoning_run_id: UUID | None
    alignment_score: Decimal
    alignment_label: ExplanationAlignmentLabel
    summary: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ExplanationComparisonFindingRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    comparison_run_id: UUID
    finding_type: ExplanationComparisonFindingType
    severity: ExplanationComparisonSeverity
    code: str
    message: str
    source_reference: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


class ExplanationComparisonResponse(ApiSchema):
    comparison_run: ExplanationComparisonRunRead
    findings: list[ExplanationComparisonFindingRead] = Field(default_factory=list)
