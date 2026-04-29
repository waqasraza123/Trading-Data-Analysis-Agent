from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.schemas import ApiReadSchema


class PatternCandidateRead(ApiReadSchema):
    id: UUID
    analysis_run_id: UUID
    workspace_id: UUID
    symbol_id: UUID
    pattern_type: str
    bias: str
    strength_score: Decimal
    is_selected: bool
    evidence_json: list[dict[str, Any]]
    risk_notes_json: list[dict[str, Any]]
    metrics_json: dict[str, Any]
    created_at: datetime
