from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.reasoning.models import ScenarioPossibilityLabel, ScenarioType
from app.modules.scenario_outcomes.models import (
    ScenarioOutcomeEvaluationStatus,
    ScenarioOutcomeSummaryRunStatus,
    ScenarioOutcomeSupportLabel,
)


class ScenarioHypothesisOutcomeRequest(ApiSchema):
    horizon_minutes: int | None = Field(default=None, gt=0)
    force_recompute: bool = False


class ReasoningRunScenarioOutcomesRequest(ApiSchema):
    horizons_minutes: list[int] | None = None
    force_recompute: bool = False

    @model_validator(mode="after")
    def validate_horizons(self) -> "ReasoningRunScenarioOutcomesRequest":
        if self.horizons_minutes is not None:
            self.horizons_minutes = normalize_horizons(self.horizons_minutes)
        return self


class ScenarioOutcomeSummaryFilters(ApiSchema):
    scenario_type: ScenarioType | None = None
    support_label: ScenarioOutcomeSupportLabel | None = None
    provider: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=160)
    reasoning_run_id: UUID | None = None
    signal_id: UUID | None = None
    horizon_minutes: int | None = Field(default=None, gt=0)
    start_time: datetime | None = None
    end_time: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self) -> "ScenarioOutcomeSummaryFilters":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class ScenarioOutcomeSummaryRequest(ApiSchema):
    workspace_id: UUID
    filters: ScenarioOutcomeSummaryFilters = Field(default_factory=ScenarioOutcomeSummaryFilters)


class ScenarioHypothesisOutcomeRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    scenario_hypothesis_id: UUID
    reasoning_run_id: UUID
    signal_id: UUID | None
    analysis_run_id: UUID | None
    outcome_id: UUID | None
    horizon_minutes: int | None
    evaluation_version: str
    scenario_type: ScenarioType
    possibility_label: ScenarioPossibilityLabel
    evaluation_status: ScenarioOutcomeEvaluationStatus
    support_label: ScenarioOutcomeSupportLabel
    support_score: Decimal
    matched_outcome_label: str | None
    matched_evidence_json: list[str]
    conflicting_evidence_json: list[str]
    summary: str
    created_at: datetime
    updated_at: datetime


class ReasoningRunScenarioOutcomesRead(ApiSchema):
    reasoning_run_id: UUID
    outcomes: list[ScenarioHypothesisOutcomeRead]


class ScenarioOutcomeSummaryRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    status: ScenarioOutcomeSummaryRunStatus
    summary_version: str
    filters_json: dict[str, Any]
    evaluated_count: int
    supported_count: int
    partially_supported_count: int
    contradicted_count: int
    inconclusive_count: int
    summary: str
    created_at: datetime
    updated_at: datetime


def normalize_horizons(horizons: list[int]) -> list[int]:
    normalized = sorted({horizon for horizon in horizons if horizon > 0})
    if not normalized:
        msg = "At least one positive horizon is required"
        raise ValueError(msg)
    return normalized
