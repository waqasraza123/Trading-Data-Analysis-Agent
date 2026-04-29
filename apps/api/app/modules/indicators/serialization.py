from decimal import Decimal
from typing import Any


def serialize_indicator_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: serialize_indicator_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_indicator_value(item) for item in value]
    return value


def serialize_indicator_map(indicators: dict[str, Any]) -> dict[str, object]:
    return {key: serialize_indicator_value(value) for key, value in indicators.items()}
