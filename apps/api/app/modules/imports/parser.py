from csv import DictReader
from io import StringIO

from pydantic import ValidationError

from app.modules.candles.normalizer import RawCandlePayload

REQUIRED_CSV_COLUMNS = frozenset({"timestamp", "open", "high", "low", "close"})


class ParsedCandleRow:
    def __init__(
        self,
        row_number: int,
        payload: RawCandlePayload,
        raw_row: dict[str, object],
    ) -> None:
        self.row_number = row_number
        self.payload = payload
        self.raw_row = raw_row


class ParsedRowError:
    def __init__(
        self,
        row_number: int,
        error_code: str,
        error_message: str,
        raw_row: dict[str, object],
    ) -> None:
        self.row_number = row_number
        self.error_code = error_code
        self.error_message = error_message
        self.raw_row = raw_row


class CsvParseResult:
    def __init__(
        self,
        rows: list[ParsedCandleRow],
        errors: list[ParsedRowError],
    ) -> None:
        self.rows = rows
        self.errors = errors


def parse_csv_candles(csv_text: str) -> CsvParseResult:
    reader = DictReader(StringIO(csv_text))
    if reader.fieldnames is None:
        return CsvParseResult(rows=[], errors=[missing_header_error()])

    normalized_columns = {column.strip() for column in reader.fieldnames}
    missing_columns = sorted(REQUIRED_CSV_COLUMNS - normalized_columns)
    if missing_columns:
        return CsvParseResult(rows=[], errors=[missing_columns_error(missing_columns)])

    rows: list[ParsedCandleRow] = []
    errors: list[ParsedRowError] = []
    for row_number, row in enumerate(reader, start=2):
        raw_row = {key.strip(): value for key, value in row.items() if key is not None}
        try:
            payload = RawCandlePayload.model_validate(raw_row)
        except ValidationError as error:
            errors.append(
                ParsedRowError(
                    row_number=row_number,
                    error_code="invalid_row",
                    error_message=error.errors()[0]["msg"],
                    raw_row=raw_row,
                )
            )
            continue
        rows.append(ParsedCandleRow(row_number=row_number, payload=payload, raw_row=raw_row))
    return CsvParseResult(rows=rows, errors=errors)


def missing_header_error() -> ParsedRowError:
    return ParsedRowError(
        row_number=0,
        error_code="missing_required_column",
        error_message="CSV header row is required",
        raw_row={},
    )


def missing_columns_error(missing_columns: list[str]) -> ParsedRowError:
    return ParsedRowError(
        row_number=0,
        error_code="missing_required_column",
        error_message=f"Missing required columns: {', '.join(missing_columns)}",
        raw_row={"missing_columns": missing_columns},
    )
