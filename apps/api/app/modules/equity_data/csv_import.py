import csv
from dataclasses import dataclass, field
from io import StringIO
from typing import Any

from pydantic import ValidationError

from app.core.errors import AppError
from app.modules.equity_data.normalizer import normalize_ticker, safe_reference
from app.modules.equity_data.schemas import EquityImportRow

CSV_IMPORT_ALLOWED_COLUMNS = {
    "ticker",
    "symbol",
    "name",
    "company_name",
    "companyname",
    "exchange",
    "sector",
    "industry",
    "currency",
    "country",
    "asset_type",
    "assettype",
    "market_cap",
    "marketcap",
    "average_volume",
    "averagevolume",
    "shares_float",
    "sharesfloat",
    "is_etf",
    "isetf",
    "is_active",
    "isactive",
}


@dataclass(frozen=True)
class EquityCsvRowError:
    row_number: int | None
    error_code: str
    error_message: str
    raw_item_json: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EquityCsvParseResult:
    rows: list[EquityImportRow]
    errors: list[EquityCsvRowError]
    redacted_preview: list[dict[str, Any]]
    received_count: int


def parse_equity_universe_csv(
    content: bytes,
    max_bytes: int,
    max_rows: int,
) -> EquityCsvParseResult:
    if len(content) > max_bytes:
        raise AppError(413, "equity_data_file_too_large", "CSV file is too large")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise AppError(422, "equity_data_csv_encoding_invalid", "CSV must be UTF-8") from error
    if not text.strip():
        raise AppError(422, "equity_data_csv_empty", "CSV file is empty")
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise AppError(422, "equity_data_csv_header_required", "CSV header is required")
    headers = [normalize_header(header) for header in reader.fieldnames]
    if "ticker" not in headers and "symbol" not in headers:
        raise AppError(
            422,
            "equity_data_csv_ticker_header_required",
            "CSV requires ticker or symbol header",
        )
    rows: list[EquityImportRow] = []
    errors: list[EquityCsvRowError] = []
    preview: list[dict[str, Any]] = []
    received_count = 0
    for row_number, raw_row in enumerate(reader, start=2):
        if received_count >= max_rows:
            raise AppError(
                422,
                "equity_data_csv_row_limit_exceeded",
                "CSV row limit exceeded for current safe staging support",
            )
        if raw_row is None:
            continue
        received_count += 1
        sanitized = sanitized_csv_row(raw_row)
        if len(preview) < 5:
            preview.append(safe_reference(sanitized))
        if not any(str(value or "").strip() for value in raw_row.values()):
            continue
        try:
            parsed = EquityImportRow.model_validate(normalized_import_row(sanitized))
            rows.append(parsed)
        except (AppError, ValidationError, ValueError) as error:
            errors.append(
                EquityCsvRowError(
                    row_number=row_number,
                    error_code=error_code(error),
                    error_message=error_message(error),
                    raw_item_json=safe_reference(sanitized),
                )
            )
    if not rows:
        raise AppError(422, "equity_data_csv_no_valid_rows", "CSV has no valid ticker rows")
    return EquityCsvParseResult(
        rows=rows,
        errors=errors,
        redacted_preview=preview,
        received_count=received_count,
    )


def sanitized_csv_row(raw_row: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in raw_row.items():
        if key is None:
            continue
        normalized_key = normalize_header(key)
        if normalized_key not in CSV_IMPORT_ALLOWED_COLUMNS:
            row[normalized_key] = safe_reference({normalized_key: value}).get(normalized_key)
            continue
        row[normalized_key] = str(value).strip() if value is not None else None
    return row


def normalized_import_row(row: dict[str, Any]) -> dict[str, Any]:
    ticker_value = row.get("ticker") or row.get("symbol")
    ticker = normalize_ticker(str(ticker_value) if ticker_value is not None else None)
    values = {
        "ticker": ticker,
        "companyName": optional_row_value(row, "company_name")
        or optional_row_value(row, "companyname")
        or optional_row_value(row, "name"),
        "exchange": optional_row_value(row, "exchange"),
        "sector": optional_row_value(row, "sector"),
        "industry": optional_row_value(row, "industry"),
        "country": optional_row_value(row, "country"),
        "currency": optional_row_value(row, "currency"),
        "marketCap": optional_row_value(row, "market_cap") or optional_row_value(row, "marketcap"),
        "averageVolume": optional_row_value(row, "average_volume")
        or optional_row_value(row, "averagevolume"),
        "sharesFloat": optional_row_value(row, "shares_float")
        or optional_row_value(row, "sharesfloat"),
        "isEtf": optional_row_value(row, "is_etf") or optional_row_value(row, "isetf"),
        "isActive": optional_row_value(row, "is_active") or optional_row_value(row, "isactive"),
        "rawReferenceJson": safe_reference(
            {
                "provider": "csv_equity_import",
                "ticker": ticker,
                "assetType": optional_row_value(row, "asset_type")
                or optional_row_value(row, "assettype")
                or "stock",
            }
        ),
    }
    return {key: value for key, value in values.items() if value is not None}


def normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def optional_row_value(row: dict[str, Any], key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def error_code(error: Exception) -> str:
    if isinstance(error, AppError):
        return error.code
    return "equity_data_csv_row_invalid"


def error_message(error: Exception) -> str:
    if isinstance(error, AppError):
        return error.message
    if isinstance(error, ValidationError):
        return "CSV row failed validation"
    return str(error) or "CSV row failed validation"
