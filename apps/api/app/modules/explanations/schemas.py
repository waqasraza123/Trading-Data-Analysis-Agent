from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.schemas import ApiReadSchema
from app.modules.explanations.models import ExplanationSafetyStatus, ExplanationType


class DeterministicExplanationRead(ApiReadSchema):
    id: UUID
    signal_id: UUID
    analysis_run_id: UUID
    workspace_id: UUID
    template_version: str
    explanation_type: ExplanationType
    short_summary: str
    market_behavior: str
    evidence_summary: str
    confidence_summary: str
    risk_summary: str
    no_signal_summary: str | None
    full_text: str
    source_snapshot_json: dict[str, Any]
    safety_status: ExplanationSafetyStatus
    blocked_terms_json: list[str]
    created_at: datetime
    updated_at: datetime
