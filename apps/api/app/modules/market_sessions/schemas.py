from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.schemas import ApiReadSchema
from app.modules.market_sessions.models import MarketSessionLabel


class MarketSessionContextRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    analysis_run_id: UUID | None
    signal_id: UUID | None
    symbol_id: UUID
    timeframe: str
    context_time: datetime
    timezone_name: str
    session_version: str
    session_label: MarketSessionLabel
    confidence_score: Decimal
    context_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
