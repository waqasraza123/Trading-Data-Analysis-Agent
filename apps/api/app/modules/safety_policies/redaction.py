from __future__ import annotations

from collections.abc import Mapping, Sequence

REDACTION_VALUE = "[REDACTED]"


def normalize_key(value: str) -> str:
    return value.lower().replace("-", "_").replace(" ", "_")


def is_sensitive_key(key: str, secret_keys: Sequence[str]) -> bool:
    normalized_key = normalize_key(key)
    return any(normalize_key(secret_key) in normalized_key for secret_key in secret_keys)


def redact_payload(payload: object, secret_keys: Sequence[str]) -> object:
    if isinstance(payload, Mapping):
        return {
            key: REDACTION_VALUE
            if is_sensitive_key(str(key), secret_keys)
            else redact_payload(value, secret_keys)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redact_payload(item, secret_keys) for item in payload]
    if isinstance(payload, tuple):
        return tuple(redact_payload(item, secret_keys) for item in payload)
    return payload


def summarize_payload(payload: object) -> dict[str, object]:
    if isinstance(payload, Mapping):
        return {
            "type": "object",
            "keys": sorted(str(key) for key in payload),
        }
    if isinstance(payload, Sequence) and not isinstance(payload, str):
        return {
            "type": "array",
            "length": len(payload),
        }
    if isinstance(payload, str):
        return {
            "type": "text",
            "length": len(payload),
        }
    return {
        "type": type(payload).__name__,
    }
