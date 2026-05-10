from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "database_url",
    "password",
    "private_key",
    "secret",
    "token",
)

RAW_PAYLOAD_KEY_PARTS = (
    "base64",
    "binary",
    "bytes",
    "candle_series",
    "candles",
    "image",
    "ocr_payload",
    "provider_payload",
    "raw_candles",
    "raw_image",
    "raw_payload",
    "screenshot",
)

UNSAFE_TEXT_PHRASES = (
    "buy now",
    "sell now",
    "enter trade",
    "exit trade",
    "guaranteed",
    "guaranteed profit",
    "place order",
    "risk-free",
    "use leverage",
)


@dataclass
class ContextPackRedactionState:
    redacted_paths: list[str] = field(default_factory=list)
    truncated_paths: dict[str, dict[str, int]] = field(default_factory=dict)
    unsafe_text_paths: list[str] = field(default_factory=list)

    def redaction_summary(self) -> dict[str, Any]:
        return {
            "redactedPaths": sorted(set(self.redacted_paths)),
            "unsafeTextPaths": sorted(set(self.unsafe_text_paths)),
            "redactedPathCount": len(set(self.redacted_paths)),
            "unsafeTextPathCount": len(set(self.unsafe_text_paths)),
        }

    def truncation_summary(self) -> dict[str, Any]:
        return self.truncated_paths


def safe_value(
    value: object,
    state: ContextPackRedactionState,
    path: str = "root",
    max_text_length: int = 4000,
) -> object:
    if isinstance(value, Mapping):
        return safe_mapping(value, state, path, max_text_length)
    if isinstance(value, list | tuple):
        return [
            safe_value(item, state, f"{path}[{index}]", max_text_length)
            for index, item in enumerate(value)
        ]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return safe_text(value, state, path, max_text_length)
    return value


def safe_mapping(
    value: Mapping[str, Any],
    state: ContextPackRedactionState,
    path: str,
    max_text_length: int,
) -> dict[str, Any]:
    safe_items: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key)
        key_path = f"{path}.{key_text}"
        normalized_key = normalize_key(key_text)
        if any(part in normalized_key for part in SECRET_KEY_PARTS):
            safe_items[key_text] = "[redacted]"
            state.redacted_paths.append(key_path)
        elif any(part in normalized_key for part in RAW_PAYLOAD_KEY_PARTS):
            safe_items[key_text] = raw_payload_summary(item)
            state.redacted_paths.append(key_path)
        else:
            safe_items[key_text] = safe_value(item, state, key_path, max_text_length)
    return safe_items


def safe_text(
    value: str,
    state: ContextPackRedactionState,
    path: str,
    max_text_length: int,
) -> str:
    sanitized = value
    lowered = sanitized.lower()
    for phrase in UNSAFE_TEXT_PHRASES:
        while phrase in lowered:
            start = lowered.index(phrase)
            end = start + len(phrase)
            sanitized = (
                sanitized[:start] + "[redacted unsafe market-action language]" + sanitized[end:]
            )
            lowered = sanitized.lower()
            state.unsafe_text_paths.append(path)
    if len(sanitized) <= max_text_length:
        return sanitized
    state.truncated_paths[path] = {
        "originalLength": len(sanitized),
        "returnedLength": max_text_length,
    }
    return sanitized[:max_text_length]


def bounded_items(
    section_name: str,
    items: Sequence[object],
    limit: int,
    state: ContextPackRedactionState,
    max_text_length: int,
) -> dict[str, Any]:
    returned_items = [
        safe_value(item, state, f"{section_name}.items[{index}]", max_text_length)
        for index, item in enumerate(items[:limit])
    ]
    total_count = len(items)
    if total_count > limit:
        state.truncated_paths[section_name] = {
            "originalLength": total_count,
            "returnedLength": len(returned_items),
        }
    return {
        "items": returned_items,
        "returnedCount": len(returned_items),
        "totalCount": total_count,
        "truncated": total_count > limit,
    }


def summarize_snapshot(
    section_name: str,
    snapshot: Mapping[str, Any] | None,
    state: ContextPackRedactionState,
    max_text_length: int,
) -> dict[str, Any]:
    if snapshot is None:
        return {"present": False}
    safe_snapshot = safe_value(dict(snapshot), state, section_name, max_text_length)
    if not isinstance(safe_snapshot, dict):
        return {"present": False}
    return {
        "present": True,
        "keyCount": len(safe_snapshot),
        "keys": sorted(safe_snapshot)[:50],
        "snapshot": safe_snapshot,
    }


def raw_payload_summary(value: object) -> dict[str, Any]:
    if value is None:
        return {"redacted": True, "present": False}
    if isinstance(value, Mapping):
        return {
            "redacted": True,
            "present": True,
            "keyCount": len(value),
            "keys": sorted(str(key) for key in value)[:50],
        }
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return {"redacted": True, "present": True, "itemCount": len(value)}
    return {"redacted": True, "present": True}


def normalize_key(value: str) -> str:
    normalized = []
    for character in value:
        if character.isupper():
            normalized.append("_")
            normalized.append(character.lower())
        else:
            normalized.append(character.lower())
    return "".join(normalized).strip("_")
