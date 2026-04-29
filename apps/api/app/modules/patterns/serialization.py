from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import cast


def serialize_pattern_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): serialize_pattern_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [serialize_pattern_value(item) for item in value]
    return value


def serialize_pattern_list(values: list[dict[str, object]]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], serialize_pattern_value(values))


def serialize_pattern_map(values: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], serialize_pattern_value(values))
