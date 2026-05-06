from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.candle_ingestion_performance.models import CandleIngestionPerformanceStatus
from app.modules.candle_ingestion_performance.schemas import CandleIngestionCounters
from app.modules.candles.models import Candle
from app.modules.candles.schemas import NormalizedCandleInput


def resolve_performance_status(
    counters: CandleIngestionCounters,
) -> CandleIngestionPerformanceStatus:
    stored_count = counters.rows_inserted + counters.rows_updated
    warning_count = (
        counters.rows_skipped_duplicate + counters.rows_conflicted + counters.rows_failed
    )
    if stored_count == 0 and warning_count > 0:
        return CandleIngestionPerformanceStatus.FAILED
    if warning_count > 0:
        return CandleIngestionPerformanceStatus.COMPLETED_WITH_WARNINGS
    return CandleIngestionPerformanceStatus.COMPLETED


def build_diagnostics_json(
    counters: CandleIngestionCounters,
    batch_size: int,
    progress_every_rows: int,
    copy_path_enabled: bool,
    elapsed_ms: int | None,
) -> dict[str, object]:
    return {
        "batchSize": batch_size,
        "progressEveryRows": progress_every_rows,
        "copyPathEnabled": copy_path_enabled,
        "copyPathUsed": False,
        "elapsedMs": elapsed_ms,
        "storedRows": counters.rows_inserted + counters.rows_updated,
        "warningRows": counters.rows_skipped_duplicate + counters.rows_conflicted,
        "failedRows": counters.rows_failed,
    }


def serialize_existing_candle(candle: Candle | None) -> dict[str, object]:
    if candle is None:
        return {}
    return {
        "id": str(candle.id),
        "workspaceId": str(candle.workspace_id),
        "symbolId": str(candle.symbol_id),
        "sourceId": str(candle.source_id),
        "timeframe": candle.timeframe,
        "timestamp": candle.timestamp.isoformat(),
        "open": decimal_to_json(candle.open),
        "high": decimal_to_json(candle.high),
        "low": decimal_to_json(candle.low),
        "close": decimal_to_json(candle.close),
        "volume": decimal_to_json(candle.volume),
        "isFinal": candle.is_final,
    }


def serialize_incoming_candle(candle: NormalizedCandleInput) -> dict[str, object]:
    return {
        "workspaceId": str(candle.workspace_id),
        "symbolId": str(candle.symbol_id),
        "sourceId": str(candle.source_id),
        "timeframe": candle.timeframe.value,
        "timestamp": candle.timestamp.isoformat(),
        "open": decimal_to_json(candle.open),
        "high": decimal_to_json(candle.high),
        "low": decimal_to_json(candle.low),
        "close": decimal_to_json(candle.close),
        "volume": decimal_to_json(candle.volume),
        "isFinal": candle.is_final,
        "originType": candle.origin_type.value,
        "originReferenceId": uuid_to_json(candle.origin_reference_id),
    }


def decimal_to_json(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def uuid_to_json(value: UUID | None) -> str | None:
    if value is None:
        return None
    return str(value)


def datetime_to_json(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
