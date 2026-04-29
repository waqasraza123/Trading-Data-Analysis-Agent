from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.schemas import ApiReadSchema


class StrategyProfileRead(ApiReadSchema):
    id: UUID
    key: str
    name: str
    description: str
    version: str
    is_active: bool
    allowed_patterns_json: list[str]
    excluded_patterns_json: list[str]
    minimum_candidate_strength: Decimal
    minimum_confidence: Decimal
    component_weights_json: dict[str, Any]
    risk_filters_json: dict[str, Any]
    no_signal_rules_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
