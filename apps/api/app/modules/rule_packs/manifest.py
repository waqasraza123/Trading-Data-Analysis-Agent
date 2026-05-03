from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from app.modules.analysis.models import AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.data_sources.models import DataSource
from app.modules.engine_versions.registry import CURRENT_ENGINE_VERSION_BY_NAME
from app.modules.rule_packs.models import ReplaySupportStatus
from app.modules.signals.models import Signal
from app.modules.symbols.models import Symbol


def to_jsonable(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    return value


def normalize_json_object(value: object) -> dict[str, object]:
    normalized = to_jsonable(value)
    return normalized if isinstance(normalized, dict) else {}


def build_strategy_profile_snapshot(
    analysis_run: AnalysisRun,
    signal: Signal | None,
) -> dict[str, object]:
    if signal is not None and signal.strategy_profile_snapshot_json is not None:
        return {
            "selectedStrategyProfile": normalize_json_object(
                signal.strategy_profile_snapshot_json
            )
        }
    rule_set_snapshot = analysis_run.rule_set_snapshot_json or {}
    strategy_profile_snapshot = rule_set_snapshot.get("strategyProfileSnapshot")
    if isinstance(strategy_profile_snapshot, dict):
        return {"selectedStrategyProfile": normalize_json_object(strategy_profile_snapshot)}
    strategy_profiles = rule_set_snapshot.get("strategyProfiles")
    if isinstance(strategy_profiles, list):
        return {"activeStrategyProfiles": to_jsonable(strategy_profiles)}
    return {"status": "unknown"}


def build_data_source_snapshot(
    analysis_run: AnalysisRun,
    symbol: Symbol | None,
    data_source: DataSource | None,
) -> dict[str, object]:
    return normalize_json_object(
        {
            "workspaceId": analysis_run.workspace_id,
            "analysisRunId": analysis_run.id,
            "symbol": (
                {
                    "id": symbol.id,
                    "symbol": symbol.symbol,
                    "displayName": symbol.display_name,
                    "marketType": symbol.market_type,
                    "baseAsset": symbol.base_asset,
                    "quoteAsset": symbol.quote_asset,
                    "pipSize": symbol.pip_size,
                    "tickSize": symbol.tick_size,
                    "pricePrecision": symbol.price_precision,
                    "quantityPrecision": symbol.quantity_precision,
                }
                if symbol is not None
                else {"id": analysis_run.symbol_id, "status": "unknown"}
            ),
            "dataSource": (
                {
                    "id": data_source.id,
                    "name": data_source.name,
                    "sourceType": data_source.source_type,
                    "provider": data_source.provider,
                    "status": data_source.status,
                    "config": data_source.config_json,
                }
                if data_source is not None
                else {"id": analysis_run.source_id, "status": "unknown"}
            ),
        }
    )


def build_candle_policy_snapshot(analysis_run: AnalysisRun) -> dict[str, object]:
    return normalize_json_object(
        {
            "finalCandlesOnly": not analysis_run.include_partial_live_candle,
            "includePartialLiveCandle": analysis_run.include_partial_live_candle,
            "timeframe": analysis_run.timeframe,
            "sourceId": analysis_run.source_id,
            "startTime": analysis_run.start_time,
            "endTime": analysis_run.end_time,
            "warmupStartTime": analysis_run.warmup_start_time,
            "baselineStartTime": analysis_run.baseline_start_time,
        }
    )


def build_parser_snapshot(chart_runs: list[ChartScreenshotRun]) -> dict[str, object]:
    if not chart_runs:
        return {"status": "not_applicable"}
    return normalize_json_object(
        {
            "chartScreenshotRuns": [
                {
                    "id": run.id,
                    "parserName": run.parser_name,
                    "parserVersion": run.parser_version,
                    "parserSourcePath": run.parser_source_path,
                    "status": run.status,
                    "extractionConfidence": run.extraction_confidence,
                    "rawCandleCount": run.raw_candle_count,
                    "storedCandleCount": run.stored_candle_count,
                    "parserMetadata": run.parser_metadata_json,
                    "extractionWarnings": run.extraction_warnings_json,
                    "extractedWindowStart": run.extracted_window_start,
                    "extractedWindowEnd": run.extracted_window_end,
                }
                for run in chart_runs
            ]
        }
    )


def evaluate_replay_support(engine_snapshot: Mapping[str, object] | None) -> ReplaySupportStatus:
    if engine_snapshot is None:
        return ReplaySupportStatus.UNKNOWN
    engines = engine_snapshot.get("engines")
    if not isinstance(engines, Mapping) or not engines:
        return ReplaySupportStatus.UNKNOWN
    has_unknown = False
    for engine_name, raw_engine in engines.items():
        if not isinstance(engine_name, str) or not isinstance(raw_engine, Mapping):
            has_unknown = True
            continue
        version = raw_engine.get("version")
        if not isinstance(version, str) or version == "" or version == "unknown":
            has_unknown = True
            continue
        current_definition = CURRENT_ENGINE_VERSION_BY_NAME.get(engine_name)
        if current_definition is None or current_definition.version != version:
            return ReplaySupportStatus.UNSUPPORTED
    if has_unknown:
        return ReplaySupportStatus.PARTIALLY_SUPPORTED
    return ReplaySupportStatus.SUPPORTED


def build_manifest_summary(
    analysis_run: AnalysisRun,
    signal: Signal | None,
    replay_support_status: ReplaySupportStatus,
) -> str:
    signal_fragment = f" and signal {signal.id}" if signal is not None else ""
    return (
        f"Manifest for analysis run {analysis_run.id}{signal_fragment} "
        f"using {analysis_run.analysis_mode} candles on {analysis_run.timeframe}; "
        f"replay support is {replay_support_status.value}."
    )
