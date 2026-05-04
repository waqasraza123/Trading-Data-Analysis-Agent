from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.schemas import ApiReadSchema
from app.modules.setup_context.models import (
    SetupContextDirectionalBias,
    SetupContextStatus,
    SetupQualityLabel,
)


class SetupContextRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    signal_id: UUID
    analysis_run_id: UUID
    symbol_id: UUID
    timeframe: str
    context_version: str
    status: SetupContextStatus
    directional_bias: SetupContextDirectionalBias
    setup_quality_label: SetupQualityLabel
    setup_quality_score: Decimal
    invalidation_context_json: list[dict[str, Any]]
    observation_zones_json: list[dict[str, Any]]
    target_context_zones_json: list[dict[str, Any]]
    wait_conditions_json: list[dict[str, Any]]
    avoid_reasons_json: list[dict[str, Any]]
    timeframe_agreement_json: dict[str, Any]
    data_quality_warnings_json: list[dict[str, Any]]
    risk_notes_json: list[dict[str, Any]]
    next_observations_json: list[dict[str, Any]]
    summary: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
