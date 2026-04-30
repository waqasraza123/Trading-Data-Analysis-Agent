from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.ai_intelligence.models import (
    AiIntelligenceClaimSupportStatus,
    AiIntelligenceGroundingStatus,
    AiIntelligenceInsightType,
    AiIntelligenceRunStatus,
    AiIntelligenceSafetyStatus,
    AiIntelligenceSeverity,
    AiIntelligenceSubjectType,
)


class AiIntelligenceRequest(ApiSchema):
    provider: str | None = None
    model: str | None = None
    force_recompute: bool = False


class AiArtifactRef(ApiSchema):
    artifact_type: str
    artifact_id: UUID
    label: str | None = None


class AiIntelligenceInputSnapshot(ApiSchema):
    subject_type: AiIntelligenceSubjectType
    subject_id: UUID
    workspace_id: UUID
    signal_id: UUID | None = None
    analysis_run_id: UUID | None = None
    outcome_id: UUID | None = None
    report_type: str
    artifact_refs: list[AiArtifactRef]
    report_sections: dict[str, Any]
    safety_rules: list[str]


class AiClaimOutput(ApiSchema):
    claim: str
    evidence_refs: list[AiArtifactRef] = Field(default_factory=list)
    support_status: AiIntelligenceClaimSupportStatus = AiIntelligenceClaimSupportStatus.SUPPORTED


class AiInsightOutput(ApiSchema):
    insight_type: AiIntelligenceInsightType
    severity: AiIntelligenceSeverity
    title: str
    summary: str
    rationale: str
    evidence_refs: list[AiArtifactRef] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    safe_follow_up_actions: list[str] = Field(default_factory=list)
    claims: list[AiClaimOutput] = Field(default_factory=list)


class ParsedAiIntelligence(ApiSchema):
    summary: str
    insights: list[AiInsightOutput]
    limitations: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    error_message: str | None = None


class AiIntelligenceRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    subject_type: AiIntelligenceSubjectType
    subject_id: UUID
    signal_id: UUID | None
    analysis_run_id: UUID | None
    outcome_id: UUID | None
    provider: str
    model: str
    prompt_version: str
    status: AiIntelligenceRunStatus
    input_snapshot_json: dict[str, Any]
    output_json: dict[str, Any] | None
    output_text: str | None
    safety_status: AiIntelligenceSafetyStatus
    grounding_status: AiIntelligenceGroundingStatus
    blocked_terms_json: list[str]
    grounding_issues_json: list[str]
    tokens_input: int | None
    tokens_output: int | None
    estimated_cost: Decimal | None
    latency_ms: int | None
    error_message: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AiIntelligenceInsightRead(ApiReadSchema):
    id: UUID
    run_id: UUID
    workspace_id: UUID
    insight_type: AiIntelligenceInsightType
    severity: AiIntelligenceSeverity
    title: str
    summary: str
    rationale: str
    evidence_refs_json: list[dict[str, Any]]
    limitations_json: list[str]
    safe_follow_up_actions_json: list[str]
    sort_order: int
    created_at: datetime


class AiIntelligenceClaimRead(ApiReadSchema):
    id: UUID
    run_id: UUID
    insight_id: UUID | None
    workspace_id: UUID
    claim_text: str
    support_status: AiIntelligenceClaimSupportStatus
    evidence_refs_json: list[dict[str, Any]]
    sort_order: int
    created_at: datetime


class AiIntelligenceResponse(ApiSchema):
    run: AiIntelligenceRunRead
    summary: str
    insights: list[AiIntelligenceInsightRead]
    claims: list[AiIntelligenceClaimRead]
    limitations: list[str] = Field(default_factory=list)
