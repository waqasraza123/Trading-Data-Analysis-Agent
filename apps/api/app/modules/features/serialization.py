from datetime import datetime
from decimal import Decimal
from typing import Any


def serialize_feature_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serialize_feature_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_feature_value(item) for item in value]
    return value


def serialize_feature_map(features: dict[str, Any]) -> dict[str, object]:
    return {key: serialize_feature_value(value) for key, value in features.items()}
