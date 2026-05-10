import csv
from io import StringIO
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.modules.synthetic_fixtures.schemas import SyntheticFixtureCandle

CSV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def candle_dicts(candles: list[SyntheticFixtureCandle]) -> list[dict[str, object]]:
    return [candle.model_dump(mode="json") for candle in candles]


def candles_to_csv(candles: list[SyntheticFixtureCandle]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for candle in candles:
        writer.writerow(
            {
                "timestamp": candle.timestamp.isoformat().replace("+00:00", "Z"),
                "open": str(candle.open),
                "high": str(candle.high),
                "low": str(candle.low),
                "close": str(candle.close),
                "volume": "" if candle.volume is None else str(candle.volume),
            }
        )
    return output.getvalue()


def build_json_import_payload(
    *,
    workspace_id: UUID | None,
    user_id: UUID | None,
    source_id: UUID | None,
    symbol_id: UUID | None,
    timeframe: str,
    candles: list[SyntheticFixtureCandle],
) -> dict[str, Any]:
    if workspace_id is None or source_id is None or symbol_id is None:
        raise AppError(
            422,
            "json_import_identifiers_required",
            "workspace_id, source_id, and symbol_id are required for JSON import payload output",
        )
    payload: dict[str, Any] = {
        "workspaceId": str(workspace_id),
        "sourceId": str(source_id),
        "symbolId": str(symbol_id),
        "timeframe": timeframe,
        "candles": candle_dicts(candles),
    }
    if user_id is not None:
        payload["userId"] = str(user_id)
    return payload
