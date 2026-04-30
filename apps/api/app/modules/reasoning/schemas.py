from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.reasoning.models import (
    ReasoningGroundingStatus,
    ReasoningRunStatus,
    ReasoningSafetyStatus,
    ReasoningSourceType,
    ReasoningType,
    ScenarioPossibilityLabel,
    ScenarioType,
)


class ScenarioReasoningRequest(ApiSchema):
    provider: str | None = None
    model: str | None = None
    force_recompute: bool = False


class ScenarioReasoningInputSnapshot(ApiSchema):
    signal_id: UUID
    analysis_run_id: UUID
    workspace_id: UUID
    symbol_id: UUID
    symbol: str
    timeframe: str
    analysis_window: dict[str, object]
    classification_status: str
    bias: str
    pattern_type: str | None
    strategy_profile_key: str | None
    strategy_profile_version: str | None
    confidence_score: str
    confidence_label: str
    signal_summary: str
    no_signal_reason: str | None
    confidence_components: list[dict[str, object]]
    signal_evidence: list[dict[str, object]]
    risk_notes: list[dict[str, object]]
    deterministic_explanation: dict[str, object] | None
    news_correlations: list[dict[str, object]]
    latest_signal_outcomes: list[dict[str, object]]
    outcome_history: dict[str, object]
    feature_summary: dict[str, object] | None
    indicator_summary: dict[str, object] | None
    replay_metadata: dict[str, object] | None
    screenshot_decision_metadata: dict[str, object] | None
    truncation: dict[str, int]


class ScenarioOutput(ApiSchema):
    scenario_type: ScenarioType
    scenario_label: str
    possibility_label: ScenarioPossibilityLabel
    supporting_evidence: list[str] = Field(default_factory=list)
    conflicting_evidence: list[str] = Field(default_factory=list)
    outcome_history: dict[str, object] | None = None
    next_observations: list[str] = Field(default_factory=list)
    suggested_backend_actions: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)


class ParsedScenarioReasoning(ApiSchema):
    summary: str
    scenarios: list[ScenarioOutput]
    limitations: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    error_message: str | None = None


class ReasoningRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    analysis_run_id: UUID | None
    signal_id: UUID | None
    outcome_id: UUID | None
    source_type: ReasoningSourceType
    provider: str
    model: str
    prompt_version: str
    reasoning_type: ReasoningType
    status: ReasoningRunStatus
    input_snapshot_json: dict[str, Any]
    output_json: dict[str, Any] | None
    output_text: str | None
    safety_status: ReasoningSafetyStatus
    grounding_status: ReasoningGroundingStatus
    blocked_terms_json: list[str]
    grounding_issues_json: list[str]
    tokens_input: int | None
    tokens_output: int | None
    estimated_cost: Decimal | None
    latency_ms: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ScenarioHypothesisRead(ApiReadSchema):
    id: UUID
    reasoning_run_id: UUID
    workspace_id: UUID
    analysis_run_id: UUID | None
    signal_id: UUID | None
    scenario_type: ScenarioType
    scenario_label: str
    possibility_label: ScenarioPossibilityLabel
    supporting_evidence_json: list[str]
    conflicting_evidence_json: list[str]
    outcome_history_json: dict[str, Any] | None
    next_observations_json: list[str]
    suggested_backend_actions_json: list[str]
    risk_notes_json: list[str]
    sort_order: int
    created_at: datetime


class ScenarioItemRead(ApiSchema):
    scenario_type: ScenarioType
    scenario_label: str
    possibility_label: ScenarioPossibilityLabel
    supporting_evidence: list[str]
    conflicting_evidence: list[str]
    outcome_history: dict[str, Any] | None
    next_observations: list[str]
    suggested_backend_actions: list[str]
    risk_notes: list[str]


class ScenarioReasoningResponse(ApiSchema):
    reasoning_run: ReasoningRunRead
    summary: str
    scenarios: list[ScenarioItemRead]
    limitations: list[str] = Field(default_factory=list)
