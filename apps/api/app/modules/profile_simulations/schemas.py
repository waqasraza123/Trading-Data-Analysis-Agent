from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.profile_simulations.models import (
    StrategyProfileSimulationDecisionChangeType,
    StrategyProfileSimulationRunStatus,
)

DEFAULT_PROFILE_SIMULATION_MAX_SIGNALS = 500


class ProfileSimulationProposedConfig(ApiSchema):
    minimum_candidate_strength: Decimal | None = Field(default=None, ge=0, le=1)
    minimum_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    component_weights_json: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("componentWeights", "componentWeightsJson"),
    )
    risk_filters_json: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("riskFilters", "riskFiltersJson"),
    )
    no_signal_rules_json: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("noSignalRules", "noSignalRulesJson"),
    )
    allowed_patterns_json: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("allowedPatterns", "allowedPatternsJson"),
    )
    excluded_patterns_json: list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("excludedPatterns", "excludedPatternsJson"),
    )


class ProfileSimulationFilters(ApiSchema):
    symbol_id: UUID | None = None
    timeframe: str | None = None
    pattern_type: str | None = None
    strategy_profile_key: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    max_signals: int = Field(default=DEFAULT_PROFILE_SIMULATION_MAX_SIGNALS, ge=1, le=5000)

    @model_validator(mode="after")
    def validate_window(self) -> "ProfileSimulationFilters":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class ProfileSimulationRunRequest(ApiSchema):
    workspace_id: UUID
    base_strategy_profile_key: str
    base_strategy_profile_version: str | None = None
    proposed_config: ProfileSimulationProposedConfig = Field(
        default_factory=ProfileSimulationProposedConfig
    )
    filters: ProfileSimulationFilters = Field(default_factory=ProfileSimulationFilters)
    horizons_minutes: list[int] = Field(default_factory=lambda: [15, 30, 60])

    @model_validator(mode="after")
    def validate_horizons(self) -> "ProfileSimulationRunRequest":
        self.horizons_minutes = normalize_horizons(self.horizons_minutes)
        return self


class StrategyProfileSimulationRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    base_strategy_profile_key: str
    base_strategy_profile_version: str | None
    status: StrategyProfileSimulationRunStatus
    simulation_version: str
    proposed_config_json: dict[str, Any]
    filters_json: dict[str, Any]
    horizons_json: list[int]
    sampled_signal_count: int
    included_count: int
    excluded_count: int
    changed_decision_count: int
    summary: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class StrategyProfileSimulationResultRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    simulation_run_id: UUID
    signal_id: UUID
    analysis_run_id: UUID
    symbol_id: UUID
    timeframe: str
    original_classification_status: str
    original_bias: str
    original_pattern_type: str | None
    original_confidence_score: Decimal | None
    simulated_classification_status: str
    simulated_bias: str
    simulated_pattern_type: str | None
    simulated_confidence_score: Decimal | None
    decision_change_type: StrategyProfileSimulationDecisionChangeType
    outcome_label: str | None
    horizon_minutes: int | None
    reason_json: dict[str, Any]
    created_at: datetime


class ProfileSimulationSummary(ApiSchema):
    run_id: UUID
    sampled_signal_count: int
    included_count: int
    excluded_count: int
    changed_decision_count: int
    outcome_labels: dict[str, int]
    decision_changes: dict[str, int]


def normalize_horizons(horizons: list[int]) -> list[int]:
    normalized = sorted({horizon for horizon in horizons if horizon > 0})
    if not normalized:
        msg = "At least one positive horizon is required"
        raise ValueError(msg)
    return normalized
