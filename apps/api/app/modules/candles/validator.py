from app.modules.candles.schemas import (
    CandleOriginType,
    CandleValidationCode,
    CandleValidationIssue,
    CandleValidationResult,
    NormalizedCandleInput,
)
from app.modules.candles.timeframes import timestamp_aligns_with_timeframe
from app.modules.data_sources.models import DataSource, DataSourceStatus, DataSourceType
from app.modules.symbols.models import Symbol


def validate_candle(
    candle: NormalizedCandleInput,
    symbol: Symbol,
    data_source: DataSource,
) -> CandleValidationResult:
    issues: list[CandleValidationIssue] = []
    if not symbol.is_active:
        issues.append(
            CandleValidationIssue(
                code=CandleValidationCode.INACTIVE_SYMBOL,
                message="Symbol is inactive",
                field_name="symbol_id",
            )
        )
    if data_source.status != DataSourceStatus.ACTIVE:
        issues.append(
            CandleValidationIssue(
                code=CandleValidationCode.INACTIVE_SOURCE,
                message="Data source is not active",
                field_name="source_id",
            )
        )
    if not timestamp_aligns_with_timeframe(candle.timestamp, candle.timeframe):
        issues.append(
            CandleValidationIssue(
                code=CandleValidationCode.INVALID_TIMESTAMP,
                message="Timestamp does not align with timeframe",
                field_name="timestamp",
            )
        )
    issues.extend(validate_origin_reference(candle, data_source))
    return CandleValidationResult(is_valid=len(issues) == 0, issues=issues)


def validate_origin_reference(
    candle: NormalizedCandleInput,
    data_source: DataSource,
) -> list[CandleValidationIssue]:
    expected_source_type = source_type_for_origin(candle.origin_type)
    if data_source.source_type != expected_source_type:
        return [
            CandleValidationIssue(
                code=CandleValidationCode.ORIGIN_REFERENCE_MISMATCH,
                message="Candle origin type does not match data source type",
                field_name="origin_type",
            )
        ]
    return []


def source_type_for_origin(origin_type: CandleOriginType) -> DataSourceType:
    match origin_type:
        case CandleOriginType.CSV_IMPORT:
            return DataSourceType.CSV_UPLOAD
        case CandleOriginType.JSON_IMPORT:
            return DataSourceType.JSON_IMPORT
        case CandleOriginType.LIVE_FEED:
            return DataSourceType.WEBSOCKET_LIVE
        case CandleOriginType.API_POLLING:
            return DataSourceType.API_POLLING
        case CandleOriginType.MANUAL_SEED:
            return DataSourceType.MANUAL_SEED
        case CandleOriginType.CHART_SCREENSHOT:
            return DataSourceType.CHART_SCREENSHOT
        case CandleOriginType.DERIVED_AGGREGATION:
            return DataSourceType.DERIVED_AGGREGATION
