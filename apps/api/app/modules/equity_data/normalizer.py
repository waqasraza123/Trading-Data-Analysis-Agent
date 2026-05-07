from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation

from app.core.errors import AppError
from app.modules.provider_credentials.redaction import redact_payload

MAX_REFERENCE_TEXT_LENGTH = 8000


def normalize_provider(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise AppError(422, "equity_data_provider_required", "Provider is required")
    return normalized


def normalize_ticker(value: str | None) -> str:
    if value is None:
        raise AppError(422, "equity_data_ticker_required", "Ticker is required")
    normalized = value.strip().upper()
    if not normalized:
        raise AppError(422, "equity_data_ticker_required", "Ticker is required")
    if len(normalized) > 32 or any(character.isspace() for character in normalized):
        raise AppError(422, "equity_data_ticker_invalid", "Ticker is invalid")
    return normalized


def optional_text(value: object, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized[:max_length]


def optional_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        parsed = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError) as error:
        raise AppError(422, "equity_data_decimal_invalid", "Numeric field is invalid") from error
    if parsed < 0:
        raise AppError(422, "equity_data_decimal_negative", "Numeric field must be non-negative")
    return parsed


def optional_bool(value: object) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None


def parse_event_date(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    normalized = str(value).strip()
    if not normalized:
        raise AppError(422, "equity_data_event_date_required", "Event date is required")
    try:
        return date.fromisoformat(normalized[:10])
    except ValueError as error:
        raise AppError(422, "equity_data_event_date_invalid", "Event date is invalid") from error


def event_datetime(event_date: date, report_time: str | None) -> datetime:
    hour = 12
    normalized = (report_time or "").strip().lower()
    if normalized in {"before_market", "pre_market", "bmo", "morning"}:
        hour = 12
    if normalized in {"after_market", "post_market", "amc", "evening"}:
        hour = 21
    return datetime.combine(event_date, time(hour=hour), tzinfo=UTC)


def safe_reference(value: object) -> dict[str, object]:
    redacted = redact_payload(value)
    if not isinstance(redacted, dict):
        redacted = {"value": redacted}
    serialized = str(redacted)
    if len(serialized) <= MAX_REFERENCE_TEXT_LENGTH:
        return redacted
    return {
        "truncated": True,
        "keys": sorted(str(key) for key in redacted),
        "originalLength": len(serialized),
    }


def snake_or_camel(row: dict[str, object], snake_key: str, camel_key: str) -> object:
    if snake_key in row:
        return row[snake_key]
    return row.get(camel_key)
