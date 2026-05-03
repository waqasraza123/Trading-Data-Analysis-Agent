from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.intelligence_quality.models import (
    IntelligenceQualityFindingType,
    IntelligenceQualityLabel,
    IntelligenceQualityRunStatus,
    IntelligenceQualitySeverity,
    IntelligenceQualitySourceType,
    ShadowAgreement,
)
from app.modules.signals.models import (
    SignalBias,
    SignalClassificationStatus,
    SignalConfidenceLabel,
)


class IntelligenceQualityRunRequest(ApiSchema):
    include_shadow_classification: bool = True
    force_recompute: bool = False


class IntelligenceQualityRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    analysis_run_id: UUID | None
    signal_id: UUID | None
    source_type: IntelligenceQualitySourceType
    status: IntelligenceQualityRunStatus
    quality_score: Decimal
    quality_label: IntelligenceQualityLabel
    gate_version: str
    shadow_version: str
    checked_at: datetime
    summary: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class IntelligenceQualityFindingRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    quality_run_id: UUID
    finding_type: IntelligenceQualityFindingType
    severity: IntelligenceQualitySeverity
    code: str
    title: str
    message: str
    artifact_type: str
    artifact_id: UUID | None
    expected_value: str | None
    observed_value: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


class ShadowClassificationResultRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    quality_run_id: UUID
    analysis_run_id: UUID
    signal_id: UUID | None
    strategy_profile_key: str
    strategy_profile_version: str
    classification_status: SignalClassificationStatus
    bias: SignalBias
    pattern_type: str | None
    confidence_score: Decimal | None
    confidence_label: SignalConfidenceLabel | None
    selected_candidate_id: UUID | None
    agreement_with_final: ShadowAgreement
    disagreement_reason: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


class IntelligenceQualityRunSummary(ApiSchema):
    id: UUID
    quality_score: Decimal
    quality_label: IntelligenceQualityLabel
    status: IntelligenceQualityRunStatus


class IntelligenceQualityResponse(ApiSchema):
    quality_run: IntelligenceQualityRunRead
    findings: list[IntelligenceQualityFindingRead] = Field(default_factory=list)
    shadow_classifications: list[ShadowClassificationResultRead] = Field(default_factory=list)
