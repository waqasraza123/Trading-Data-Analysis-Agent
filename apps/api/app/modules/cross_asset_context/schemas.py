from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.cross_asset_context.models import (
    CrossAssetAlignmentLabel,
    CrossAssetContextRunStatus,
    CrossAssetDataQualityLabel,
    CrossAssetLeadLagLabel,
)


class CrossAssetContextBuildRequest(ApiSchema):
    compared_symbol_ids: list[UUID] = Field(min_length=1)
    force_recompute: bool = False

    @field_validator("compared_symbol_ids")
    @classmethod
    def dedupe_compared_symbols(cls, value: list[UUID]) -> list[UUID]:
        seen: set[UUID] = set()
        result: list[UUID] = []
        for symbol_id in value:
            if symbol_id not in seen:
                seen.add(symbol_id)
                result.append(symbol_id)
        return result


class CrossAssetContextRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    analysis_run_id: UUID | None
    signal_id: UUID | None
    base_symbol_id: UUID
    timeframe: str
    source_id: UUID | None
    context_version: str
    status: CrossAssetContextRunStatus
    start_time: datetime
    end_time: datetime
    compared_symbol_count: int
    result_count: int
    summary: str
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CrossAssetContextResultRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    context_run_id: UUID
    base_symbol_id: UUID
    compared_symbol_id: UUID
    timeframe: str
    start_time: datetime
    end_time: datetime
    base_move: Decimal
    compared_move: Decimal
    base_direction: str
    compared_direction: str
    correlation_score: Decimal
    alignment_label: CrossAssetAlignmentLabel
    lead_lag_offset_candles: int | None
    lead_lag_label: CrossAssetLeadLagLabel
    divergence_score: Decimal
    data_quality_label: CrossAssetDataQualityLabel
    metadata_json: dict[str, Any]
    created_at: datetime
