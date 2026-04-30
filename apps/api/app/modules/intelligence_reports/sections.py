from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

MAX_EVIDENCE_ROWS = 50
MAX_AUDIT_EVENTS = 100
MAX_SCENARIO_HYPOTHESES = 10
MAX_ACTION_ITEMS = 50
MAX_CORRELATIONS = 20
MAX_PATTERN_CANDIDATES = 25
MAX_DIAGNOSTICS = 20
MAX_RECOMMENDATIONS = 20

BANNED_REPORT_PHRASES = (
    "buy now",
    "sell now",
    "enter trade",
    "exit trade",
    "use leverage",
    "guaranteed profit",
    "guaranteed",
    "risk-free",
    "place order",
)

SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "credential",
    "database_url",
    "password",
    "private_key",
    "provider_secret",
    "raw_provider",
    "secret",
    "token",
)

RAW_PAYLOAD_KEY_PARTS = (
    "image",
    "screenshot",
    "raw_payload",
    "provider_payload",
    "candles",
)

SAFE_OUTCOME_TERMS = (
    "continuation",
    "reversal",
    "no follow-through",
    "partial follow-through",
    "insufficient data",
)


def bounded_items(items: Sequence[Any], limit: int) -> dict[str, Any]:
    values = [to_report_value(item) for item in items[:limit]]
    total_count = len(items)
    return {
        "items": values,
        "returned_count": len(values),
        "total_count": total_count,
        "truncated": total_count > limit,
    }


def bounded_mapping_items(items: Sequence[Mapping[str, Any]], limit: int) -> dict[str, Any]:
    values = [to_report_value(dict(item)) for item in items[:limit]]
    total_count = len(items)
    return {
        "items": values,
        "returned_count": len(values),
        "total_count": total_count,
        "truncated": total_count > limit,
    }


def grouped_evidence(items: Sequence[Mapping[str, Any]], limit: int) -> dict[str, Any]:
    bounded = bounded_mapping_items(items, limit)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in bounded["items"]:
        if isinstance(item, dict):
            grouped.setdefault(str(item.get("evidence_type") or "unknown"), []).append(item)
    return {
        **bounded,
        "grouped_by_evidence_type": grouped,
    }


def summarize_json_snapshot(snapshot: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    safe_snapshot = to_report_value(dict(snapshot))
    if not isinstance(safe_snapshot, dict):
        return None
    return {
        "key_count": len(safe_snapshot),
        "keys": sorted(str(key) for key in safe_snapshot)[:50],
        "snapshot": safe_snapshot,
    }


def to_report_value(value: object) -> object:
    if isinstance(value, Mapping):
        return redact_mapping(value)
    if isinstance(value, list | tuple):
        return [to_report_value(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def redact_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key)
        normalized_key = normalize_key(key_text)
        if any(part in normalized_key for part in SECRET_KEY_PARTS):
            result[key_text] = "[redacted]"
        elif any(part in normalized_key for part in RAW_PAYLOAD_KEY_PARTS):
            result[key_text] = summarize_raw_value(item)
        else:
            result[key_text] = to_report_value(item)
    return result


def summarize_raw_value(value: object) -> dict[str, Any]:
    if isinstance(value, list):
        return {"redacted": True, "item_count": len(value)}
    if isinstance(value, Mapping):
        return {
            "redacted": True,
            "key_count": len(value),
            "keys": sorted(str(key) for key in value),
        }
    if value is None:
        return {"redacted": True, "present": False}
    return {"redacted": True, "present": True}


def sanitize_text(value: str) -> str:
    sanitized = value
    lowered = sanitized.lower()
    for phrase in BANNED_REPORT_PHRASES:
        while phrase in lowered:
            start = lowered.index(phrase)
            end = start + len(phrase)
            sanitized = (
                sanitized[:start]
                + "[redacted unsafe trading language]"
                + sanitized[end:]
            )
            lowered = sanitized.lower()
    return sanitized


def normalize_key(value: str) -> str:
    normalized = []
    for character in value:
        if character.isupper():
            normalized.append("_")
            normalized.append(character.lower())
        else:
            normalized.append(character.lower())
    return "".join(normalized).strip("_")


def report_contains_banned_phrase(value: object) -> bool:
    serialized = str(to_report_value(value)).lower()
    return any(phrase in serialized for phrase in BANNED_REPORT_PHRASES)
