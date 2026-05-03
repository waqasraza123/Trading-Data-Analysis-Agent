from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "database_url",
    "databaseurl",
    "authorization",
    "credential",
    "private_key",
    "privatekey",
)
RAW_IMAGE_KEY_PARTS = (
    "raw_image",
    "image_bytes",
    "image_base64",
    "base64",
    "raw_bytes",
    "file_bytes",
    "raw_payload",
    "provider_payload",
)
MAX_TEXT_LENGTH = 2000
MAX_LIST_ITEMS = 50


def default_redaction_policy() -> dict[str, object]:
    return {
        "sensitiveKeyParts": list(SENSITIVE_KEY_PARTS),
        "rawImageKeyParts": list(RAW_IMAGE_KEY_PARTS),
        "maxTextLength": MAX_TEXT_LENGTH,
        "maxListItems": MAX_LIST_ITEMS,
        "rawCandleSeriesIncluded": False,
        "rawImagesIncluded": False,
        "rawProviderPayloadsIncluded": False,
    }


def redact_record(payload: dict[str, object]) -> tuple[dict[str, object], list[str]]:
    warnings: list[str] = []
    redacted = redact_value(payload, "record", warnings)
    return redacted if isinstance(redacted, dict) else {}, sorted(set(warnings))


def redact_value(value: object, path: str, warnings: list[str]) -> object:
    if isinstance(value, dict):
        return redact_mapping(value, path, warnings)
    if isinstance(value, list):
        return redact_list(value, path, warnings)
    if isinstance(value, tuple):
        return redact_list(list(value), path, warnings)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, str):
        return redact_text(value, path, warnings)
    return value


def redact_mapping(payload: dict[object, object], path: str, warnings: list[str]) -> dict[str, object]:
    redacted: dict[str, object] = {}
    for raw_key, raw_value in payload.items():
        key = str(raw_key)
        normalized_key = key.lower()
        child_path = f"{path}.{key}"
        if any(part in normalized_key for part in SENSITIVE_KEY_PARTS):
            redacted[key] = "[REDACTED]"
            warnings.append(f"redacted sensitive field {child_path}")
            continue
        if any(part in normalized_key for part in RAW_IMAGE_KEY_PARTS):
            warnings.append(f"dropped raw image field {child_path}")
            continue
        if normalized_key in {"candles", "raw_candles", "ohlc", "ohlcv", "series"}:
            warnings.append(f"dropped raw candle series field {child_path}")
            continue
        redacted[key] = redact_value(raw_value, child_path, warnings)
    return redacted


def redact_list(values: list[object], path: str, warnings: list[str]) -> list[object]:
    bounded = values[:MAX_LIST_ITEMS]
    if len(values) > MAX_LIST_ITEMS:
        warnings.append(f"truncated list {path} from {len(values)} to {MAX_LIST_ITEMS}")
    return [redact_value(item, f"{path}[]", warnings) for item in bounded]


def redact_text(value: str, path: str, warnings: list[str]) -> str:
    if len(value) <= MAX_TEXT_LENGTH:
        return value
    warnings.append(f"truncated text field {path} from {len(value)} to {MAX_TEXT_LENGTH}")
    return value[:MAX_TEXT_LENGTH]
