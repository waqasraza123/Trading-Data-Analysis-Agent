import re
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "cookie",
    "credential",
    "password",
    "private_key",
    "secret",
    "signing_secret",
    "token",
)
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
    "output_text",
    "raw_llm_output",
    "unsafe_output",
}
BLOCKED_TEXT_RE = re.compile(
    r"\b(buy|sell|entry|exit|leverage|order|position|stop[- ]?loss|take[- ]?profit)\b",
    re.IGNORECASE,
)


def sanitize_payload(payload: dict[str, object]) -> tuple[dict[str, object], list[str]]:
    warnings: list[str] = []
    sanitized = sanitize_value(payload, warnings, path="")
    if not isinstance(sanitized, dict):
        return {}, warnings
    return sanitized, sorted(set(warnings))


def sanitize_value(value: object, warnings: list[str], path: str) -> object:
    if isinstance(value, dict):
        return sanitize_mapping(value, warnings, path)
    if isinstance(value, list):
        return [sanitize_value(item, warnings, path) for item in value[:100]]
    if isinstance(value, tuple):
        return [sanitize_value(item, warnings, path) for item in value[:100]]
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


def sanitize_mapping(
    value: dict[object, object],
    warnings: list[str],
    path: str,
) -> dict[str, object]:
    sanitized: dict[str, object] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key)
        normalized_key = key.lower()
        next_path = f"{path}.{key}" if path else key
        if should_redact_key(normalized_key):
            sanitized[key] = "[redacted]"
            warnings.append(f"redacted sensitive or unsafe field at {next_path}")
            continue
        sanitized[key] = sanitize_value(raw_value, warnings, next_path)
    return sanitized


def should_redact_key(key: str) -> bool:
    if key in RAW_IMAGE_KEYS or key in RAW_SERIES_KEYS or key in UNSAFE_LLM_KEYS:
        return True
    return any(part in key for part in SECRET_KEY_PARTS)


def sanitize_text(value: str, warnings: list[str], path: str) -> str:
    normalized = value.strip()
    if BLOCKED_TEXT_RE.search(normalized):
        warnings.append(f"redacted unsafe trading language at {path or 'payload'}")
        return "[redacted unsafe trading language]"
    return normalized
