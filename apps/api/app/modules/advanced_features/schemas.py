from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.schemas import ApiReadSchema


class AdvancedFeatureSnapshotRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    analysis_run_id: UUID
    symbol_id: UUID
    timeframe: str
    feature_pack_version: str
    impulse_json: dict[str, Any]
    correction_json: dict[str, Any]
    wick_pressure_json: dict[str, Any]
    movement_efficiency_json: dict[str, Any]
    compression_expansion_json: dict[str, Any]
    swing_structure_json: dict[str, Any]
    support_resistance_json: dict[str, Any]
    exhaustion_json: dict[str, Any]
    liquidity_sweep_json: dict[str, Any]
    warnings_json: dict[str, Any]
    summary: str
    created_at: datetime
    updated_at: datetime
