from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.schemas import ApiReadSchema
from app.modules.signals.models import (
    SignalBias,
    SignalClassificationStatus,
    SignalConfidenceLabel,
)


class SignalRead(ApiReadSchema):
    id: UUID
    analysis_run_id: UUID
    workspace_id: UUID
    symbol_id: UUID
    timeframe: str
    strategy_profile_id: UUID | None
    strategy_profile_key: str | None
    strategy_profile_version: str | None
    strategy_profile_snapshot_json: dict[str, Any] | None
    bias: SignalBias
    pattern_type: str | None
    classification_status: SignalClassificationStatus
    confidence_score: Decimal
    confidence_label: SignalConfidenceLabel
    candidate_strength: Decimal | None
    selected_pattern_candidate_id: UUID | None
    pips_moved: Decimal | None
    tick_moved: Decimal | None
    movement_direction: str | None
    movement_quality: str | None
    volatility_state: str | None
    trend_state: str | None
    range_state: str | None
    summary: str
    no_signal_reason: str | None
    created_at: datetime


class SignalConfidenceComponentRead(ApiReadSchema):
    id: UUID
    signal_id: UUID
    component_name: str
    component_score: Decimal
    component_weight: Decimal
    weighted_score: Decimal
    reason: str
    created_at: datetime


class SignalEvidenceRead(ApiReadSchema):
    id: UUID
    signal_id: UUID
    evidence_type: str
    direction: str
    message: str
    numeric_value: Decimal | None
    weight: Decimal
    metadata_json: dict[str, Any]
    created_at: datetime


class SignalRiskNoteRead(ApiReadSchema):
    id: UUID
    signal_id: UUID
    code: str
    message: str
    severity: str
    metadata_json: dict[str, Any]
    created_at: datetime


class SignalClassificationRead(ApiReadSchema):
    analysis_run_id: UUID
    signal: SignalRead
    confidence_components: list[SignalConfidenceComponentRead]
    evidence: list[SignalEvidenceRead]
    risk_notes: list[SignalRiskNoteRead]
