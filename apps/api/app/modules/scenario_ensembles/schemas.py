from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.scenario_ensembles.models import (
    ScenarioConsensusLabel,
    ScenarioEnsembleItemStatus,
    ScenarioEnsembleRunStatus,
)


class ScenarioEnsembleProviderRequest(ApiSchema):
    provider: str = Field(min_length=1, max_length=32)
    model: str = Field(min_length=1, max_length=120)

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if not normalized_value:
            msg = "provider must not be empty"
            raise ValueError(msg)
        return normalized_value

    @field_validator("model")
    @classmethod
    def normalize_model(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            msg = "model must not be empty"
            raise ValueError(msg)
        return normalized_value


class ScenarioEnsembleRequest(ApiSchema):
    providers: list[ScenarioEnsembleProviderRequest] = Field(default_factory=list)
    force_recompute: bool = False

    @model_validator(mode="after")
    def validate_unique_provider_models(self) -> "ScenarioEnsembleRequest":
        seen: set[tuple[str, str]] = set()
        for provider_model in self.providers:
            key = (provider_model.provider, provider_model.model)
            if key in seen:
                msg = "providers must not contain duplicate provider/model entries"
                raise ValueError(msg)
            seen.add(key)
        return self


class ScenarioEnsembleRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    signal_id: UUID
    analysis_run_id: UUID | None
    status: ScenarioEnsembleRunStatus
    ensemble_version: str
    requested_providers_json: list[str]
    requested_models_json: list[str]
    reasoning_run_ids_json: list[str]
    consensus_score: float
    consensus_label: ScenarioConsensusLabel
    summary: str
    safety_status: str
    grounding_status: str
    error_message: str | None
    metadata_json: dict[str, object]
    created_at: datetime
    updated_at: datetime


class ScenarioEnsembleItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    ensemble_run_id: UUID
    reasoning_run_id: UUID | None
    provider: str
    model: str
    status: ScenarioEnsembleItemStatus
    scenario_types_json: list[str]
    suggested_actions_json: list[str]
    safety_status: str
    grounding_status: str
    summary: str
    error_message: str | None
    created_at: datetime


class ScenarioConsensusResultRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    ensemble_run_id: UUID
    scenario_type: str
    agreement_count: int
    disagreement_count: int
    possibility_labels_json: list[str]
    supporting_evidence_json: list[str]
    conflicting_evidence_json: list[str]
    consensus_label: ScenarioConsensusLabel
    metadata_json: dict[str, object]
    created_at: datetime


class ScenarioEnsembleResponse(ApiSchema):
    run: ScenarioEnsembleRunRead
    items: list[ScenarioEnsembleItemRead]
    consensus: list[ScenarioConsensusResultRead]
