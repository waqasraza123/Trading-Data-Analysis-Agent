from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.schemas import ApiReadSchema


class IndicatorSnapshotRead(ApiReadSchema):
    id: UUID
    analysis_run_id: UUID
    workspace_id: UUID
    symbol_id: UUID
    timeframe: str
    indicators_json: dict[str, Any]
    created_at: datetime
