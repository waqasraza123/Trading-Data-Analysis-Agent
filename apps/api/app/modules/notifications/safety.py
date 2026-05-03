import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from app.modules.safety_policies.schemas import SafetyStatus

SECRET_KEY_PARTS = {
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "cookie",
    "credential",
    "database_url",
    "password",
    "private_key",
    "secret",
    "token",
}
RAW_IMAGE_KEYS = {
    "file_bytes",
    "file_content",
    "image",
    "image_base64",
    "image_bytes",
    "raw_image",
    "screenshot_base64",
    "screenshot_bytes",
}
RAW_SERIES_KEYS = {
    "candles",
    "candle_series",
    "ohlc_rows",
    "raw_candles",
    "raw_candle_series",
}
UNSAFE_LLM_KEYS = {
    "blocked_output",
    "completion",
    "messages",
    "output_text",
    "prompt",
    "raw_llm_output",
    "unsafe_output",
}
BLOCKED_TEXT_RE = re.compile(
    r"\b(buy|sell|entry|exit|leverage|place order|execute trade|open position|"
    r"close position|stop[- ]?loss|take[- ]?profit|financial advice|"
    r"guaranteed profit|win rate|risk[- ]?free|cannot lose)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NotificationSafetyResult:
    title: str
    summary: str
    payload_json: dict[str, object]
    safety_status: SafetyStatus
    warnings: list[str] = field(default_factory=list)
    blocked_terms: list[str] = field(default_factory=list)


def sanitize_notification_delivery_payload(
    title: str,
    summary: str,
    payload_json: dict[str, object],
    max_payload_bytes: int,
) -> NotificationSafetyResult:
    warnings: list[str] = []
    blocked_terms = blocked_terms_in_text(f"{title}\n{summary}")
    sanitized_payload = sanitize_payload(payload_json, warnings)
    payload_text = json.dumps(sanitized_payload, default=str, sort_keys=True)
    blocked_terms.extend(blocked_terms_in_text(payload_text))
    unique_blocked_terms = sorted(set(blocked_terms))
    if unique_blocked_terms:
        return NotificationSafetyResult(
            title=sanitize_text(title, warnings, "title"),
            summary=sanitize_text(summary, warnings, "summary"),
            payload_json={},
            safety_status=SafetyStatus.BLOCKED,
            warnings=sorted(set(warnings)),
            blocked_terms=unique_blocked_terms,
        )
    limited_payload = enforce_payload_size(sanitized_payload, max_payload_bytes, warnings)
    status = SafetyStatus.REDACTED if warnings else SafetyStatus.PASSED
    return NotificationSafetyResult(
        title=sanitize_text(title, warnings, "title"),
        summary=sanitize_text(summary, warnings, "summary"),
        payload_json=limited_payload,
        safety_status=status,
        warnings=sorted(set(warnings)),
        blocked_terms=[],
    )


def sanitize_payload(payload: dict[str, object], warnings: list[str]) -> dict[str, object]:
    sanitized = sanitize_value(payload, warnings, "$")
    if isinstance(sanitized, dict):
        return sanitized
    return {}


def sanitize_value(value: object, warnings: list[str], path: str) -> object:
    if isinstance(value, dict):
        sanitized: dict[str, object] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            normalized_key = key.lower()
            next_path = f"{path}.{key}"
            if should_redact_key(normalized_key):
                sanitized[key] = "[redacted]"
                warnings.append(f"redacted field at {next_path}")
                continue
            sanitized[key] = sanitize_value(raw_value, warnings, next_path)
        return sanitized
    if isinstance(value, list):
        if len(value) > 100:
            warnings.append(f"truncated list at {path}")
        return [sanitize_value(item, warnings, f"{path}[]") for item in value[:100]]
    if isinstance(value, tuple):
        if len(value) > 100:
            warnings.append(f"truncated list at {path}")
        return [sanitize_value(item, warnings, f"{path}[]") for item in value[:100]]
    if isinstance(value, str):
        return sanitize_text(value, warnings, path)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if value is None or isinstance(value, bool | int | float):
        return value
    return str(value)


def should_redact_key(key: str) -> bool:
    if key in RAW_IMAGE_KEYS or key in RAW_SERIES_KEYS or key in UNSAFE_LLM_KEYS:
        return True
    return any(part in key for part in SECRET_KEY_PARTS)


def sanitize_text(value: str, warnings: list[str], path: str) -> str:
    normalized = value.strip()
    if len(normalized) > 2000:
        warnings.append(f"truncated text at {path}")
        return normalized[:2000]
    return normalized


def blocked_terms_in_text(value: str) -> list[str]:
    return sorted({match.group(0).lower() for match in BLOCKED_TEXT_RE.finditer(value)})


def enforce_payload_size(
    payload: dict[str, object],
    max_payload_bytes: int,
    warnings: list[str],
) -> dict[str, object]:
    encoded = json.dumps(payload, default=str, sort_keys=True).encode("utf-8")
    if len(encoded) <= max_payload_bytes:
        return payload
    warnings.append("truncated payload to configured byte limit")
    return {
        "truncated": True,
        "maxPayloadBytes": max_payload_bytes,
        "availableKeys": sorted(payload.keys())[:100],
    }
