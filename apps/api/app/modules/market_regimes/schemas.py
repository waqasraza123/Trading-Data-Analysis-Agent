from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.market_regimes.models import (
    DataQualityLabel,
    RangeRegime,
    RegimeConfidenceLabel,
    TrendRegime,
    VolatilityRegime,
)


class MarketRegimeGenerationRequest(ApiSchema):
    force_recompute: bool = False


class MarketRegimeContextRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    analysis_run_id: UUID
    signal_id: UUID | None
    symbol_id: UUID
    timeframe: str
    regime_version: str
    trend_regime: TrendRegime
    volatility_regime: VolatilityRegime
    range_regime: RangeRegime
    liquidity_regime: str | None
    data_quality_label: DataQualityLabel
    confidence_score: Decimal
    confidence_label: RegimeConfidenceLabel
    summary: str
    feature_inputs_json: dict[str, Any]
    indicator_inputs_json: dict[str, Any]
    warnings_json: list[dict[str, Any]]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
