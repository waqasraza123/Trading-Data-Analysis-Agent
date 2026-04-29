from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema
from app.modules.llm_explanations.models import (
    LlmExplanationGroundingStatus,
    LlmExplanationSafetyStatus,
)


class LlmExplanationInputPayload(ApiReadSchema):
    signal_id: UUID
    analysis_run_id: UUID
    workspace_id: UUID
    symbol: str
    timeframe: str
    analysis_window: dict[str, object]
    classification_status: str
    bias: str
    pattern_type: str | None
    strategy_profile_key: str | None
    strategy_profile_version: str | None
    strategy_profile_snapshot: dict[str, Any] | None
    feature_snapshot: dict[str, Any] | None
    indicator_snapshot: dict[str, Any] | None
    confidence: dict[str, object]
    confidence_components: list[dict[str, object]]
    evidence: list[dict[str, object]]
    risk_notes: list[dict[str, object]]
    deterministic_explanation: dict[str, object] | None
    movement_fields: dict[str, object]
    trend_state: str | None
    volatility_state: str | None
    range_state: str | None
    no_signal_reason: str | None
    news_correlations: list[dict[str, object]] = Field(default_factory=list)


class LlmExplanationRead(ApiReadSchema):
    id: UUID
    signal_id: UUID
    analysis_run_id: UUID
    workspace_id: UUID
    provider: str
    model: str
    prompt_version: str
    safety_status: LlmExplanationSafetyStatus
    grounding_status: LlmExplanationGroundingStatus
    blocked_terms_json: list[str]
    grounding_issues_json: list[str]
    input_json: dict[str, object] | None
    output_text: str
    tokens_input: int | None
    tokens_output: int | None
    estimated_cost: Decimal | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
