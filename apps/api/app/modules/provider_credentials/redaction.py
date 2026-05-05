from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

REDACTED_VALUE = "[redacted]"

SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "cookie",
    "password",
    "private_key",
    "secret",
    "signing_secret",
    "token",
)

REFERENCE_KEY_PARTS = (
    "secret_ref",
    "credential_ref",
    "credential_ref_id",
)


def normalize_key(value: str) -> str:
    return value.lower().replace("-", "_")


def is_sensitive_key(key: str) -> bool:
    normalized = normalize_key(key)
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def is_reference_key(key: str) -> bool:
    normalized = normalize_key(key)
    return any(part in normalized for part in REFERENCE_KEY_PARTS)


def find_sensitive_payload_paths(value: object, path: str = "$") -> list[str]:
    if isinstance(value, dict):
        paths: list[str] = []
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            next_path = f"{path}.{key}"
            if is_sensitive_key(key):
                paths.append(next_path)
            paths.extend(find_sensitive_payload_paths(raw_value, next_path))
        return paths
    if isinstance(value, list):
        paths: list[str] = []
        for index, item in enumerate(value):
            paths.extend(find_sensitive_payload_paths(item, f"{path}[{index}]"))
        return paths
    return []


def redact_payload(value: object, extra_sensitive_keys: Sequence[str] = ()) -> object:
    if isinstance(value, dict):
        return {
            str(key): REDACTED_VALUE
            if key_should_be_redacted(str(key), extra_sensitive_keys)
            else redact_payload(nested_value, extra_sensitive_keys)
            for key, nested_value in value.items()
        }
    if isinstance(value, list):
        return [redact_payload(item, extra_sensitive_keys) for item in value]
    if isinstance(value, tuple):
        return [redact_payload(item, extra_sensitive_keys) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def key_should_be_redacted(key: str, extra_sensitive_keys: Sequence[str]) -> bool:
    normalized = normalize_key(key)
    return is_sensitive_key(normalized) or any(
        normalize_key(extra_key) in normalized for extra_key in extra_sensitive_keys
    )
