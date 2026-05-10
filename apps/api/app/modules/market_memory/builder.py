from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.config import Settings
from app.modules.advanced_features.models import AdvancedFeatureSnapshot
from app.modules.analysis.models import AnalysisRun
from app.modules.candles.models import Candle
from app.modules.cross_asset_context.models import CrossAssetContextResult, CrossAssetContextRun
from app.modules.data_quality.models import DataQualityRun
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.market_memory.freshness import FreshnessThresholds, determine_freshness_label
from app.modules.market_memory.models import (
    MarketMemoryDataQualityLabel,
    MarketMemoryFreshnessLabel,
    RollingMarketStateSnapshot,
)
from app.modules.market_memory.repository import MarketMemoryRepository
from app.modules.market_regimes.models import MarketRegimeContext
from app.modules.market_sessions.models import MarketSessionContext
from app.modules.outcomes.models import SignalOutcome
from app.modules.signals.models import Signal
from app.modules.timeframe_aggregation.models import MultiTimeframeContext

JsonValue = dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None


@dataclass(frozen=True)
class MarketMemoryArtifacts:
    latest_final_candle: Candle | None
    latest_analysis_run: AnalysisRun | None
    latest_signal: Signal | None
    feature_snapshot: FeatureSnapshot | None
    indicator_snapshot: IndicatorSnapshot | None
    advanced_feature_snapshot: AdvancedFeatureSnapshot | None
    market_regime: MarketRegimeContext | None
    market_session: MarketSessionContext | None
    multi_timeframe_context: MultiTimeframeContext | None
    cross_asset_context_run: CrossAssetContextRun | None
    cross_asset_results: list[CrossAssetContextResult]
    latest_outcome: SignalOutcome | None
    latest_data_quality_run: DataQualityRun | None


class MarketMemoryBuilder:
    def __init__(self, repository: MarketMemoryRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    async def build(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        source_id: UUID | None,
    ) -> RollingMarketStateSnapshot:
        artifacts = await self.load_artifacts(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            source_id=source_id,
        )
        freshness_label = determine_freshness_label(
            latest_final_candle_time=(
                artifacts.latest_final_candle.timestamp
                if artifacts.latest_final_candle is not None
                else None
            ),
            timeframe=timeframe,
            thresholds=FreshnessThresholds(
                fresh_seconds_1m=self.settings.market_memory_fresh_seconds_1m,
                fresh_seconds_5m=self.settings.market_memory_fresh_seconds_5m,
                fresh_seconds_15m=self.settings.market_memory_fresh_seconds_15m,
                fresh_seconds_1h=self.settings.market_memory_fresh_seconds_1h,
            ),
        )
        data_quality_label = determine_data_quality_label(
            artifacts.latest_data_quality_run,
            artifacts.feature_snapshot,
        )
        context_json = build_context_json(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            timeframe=timeframe,
            state_version=self.settings.market_memory_state_version,
            data_quality_label=data_quality_label,
            freshness_label=freshness_label,
            artifacts=artifacts,
        )
        warnings_json = build_warnings_json(
            data_quality_label=data_quality_label,
            freshness_label=freshness_label,
            artifacts=artifacts,
            max_warnings=self.settings.market_memory_max_context_warnings,
        )
        return RollingMarketStateSnapshot(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            timeframe=timeframe,
            state_version=self.settings.market_memory_state_version,
            latest_final_candle_time=(
                artifacts.latest_final_candle.timestamp
                if artifacts.latest_final_candle is not None
                else None
            ),
            latest_analysis_run_id=(
                artifacts.latest_analysis_run.id
                if artifacts.latest_analysis_run is not None
                else None
            ),
            latest_signal_id=(
                artifacts.latest_signal.id if artifacts.latest_signal is not None else None
            ),
            latest_outcome_id=(
                artifacts.latest_outcome.id if artifacts.latest_outcome is not None else None
            ),
            data_quality_label=data_quality_label.value,
            freshness_label=freshness_label.value,
            trend_state=derive_trend_state(artifacts),
            volatility_state=derive_volatility_state(artifacts),
            range_state=derive_range_state(artifacts),
            market_regime_label=derive_market_regime_label(artifacts.market_regime),
            market_session_label=(
                artifacts.market_session.session_label
                if artifacts.market_session is not None
                else None
            ),
            multi_timeframe_label=(
                artifacts.multi_timeframe_context.agreement_label
                if artifacts.multi_timeframe_context is not None
                else None
            ),
            cross_asset_label=derive_cross_asset_label(artifacts.cross_asset_results),
            latest_signal_bias=(
                artifacts.latest_signal.bias if artifacts.latest_signal is not None else None
            ),
            latest_signal_pattern_type=(
                artifacts.latest_signal.pattern_type
                if artifacts.latest_signal is not None
                else None
            ),
            latest_signal_confidence_label=(
                artifacts.latest_signal.confidence_label
                if artifacts.latest_signal is not None
                else None
            ),
            context_json=context_json,
            warnings_json=warnings_json,
        )

    async def load_artifacts(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        source_id: UUID | None,
    ) -> MarketMemoryArtifacts:
        latest_final_candle = await self.repository.get_latest_final_candle(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            source_id=source_id,
        )
        latest_analysis_run = await self.repository.get_latest_completed_analysis_run(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            source_id=source_id,
        )
        analysis_run_id = latest_analysis_run.id if latest_analysis_run is not None else None
        latest_signal = await self.repository.get_latest_signal(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            analysis_run_id=analysis_run_id,
        )
        signal_id = latest_signal.id if latest_signal is not None else None
        cross_asset_context_run = await self.repository.get_cross_asset_context_run(
            analysis_run_id=analysis_run_id,
            signal_id=signal_id,
        )
        return MarketMemoryArtifacts(
            latest_final_candle=latest_final_candle,
            latest_analysis_run=latest_analysis_run,
            latest_signal=latest_signal,
            feature_snapshot=await self.repository.get_feature_snapshot(analysis_run_id),
            indicator_snapshot=await self.repository.get_indicator_snapshot(analysis_run_id),
            advanced_feature_snapshot=await self.repository.get_advanced_feature_snapshot(
                analysis_run_id
            ),
            market_regime=await self.repository.get_market_regime(
                analysis_run_id=analysis_run_id,
                signal_id=signal_id,
            ),
            market_session=await self.repository.get_market_session(
                analysis_run_id=analysis_run_id,
                signal_id=signal_id,
            ),
            multi_timeframe_context=await self.repository.get_multi_timeframe_context(
                analysis_run_id=analysis_run_id,
                signal_id=signal_id,
            ),
            cross_asset_context_run=cross_asset_context_run,
            cross_asset_results=await self.repository.list_cross_asset_results(
                context_run_id=(
                    cross_asset_context_run.id if cross_asset_context_run is not None else None
                ),
                limit=20,
            ),
            latest_outcome=await self.repository.get_latest_outcome(
                workspace_id=workspace_id,
                symbol_id=symbol_id,
                timeframe=timeframe,
                signal_id=signal_id,
            ),
            latest_data_quality_run=await self.repository.get_latest_data_quality_run(
                workspace_id=workspace_id,
                symbol_id=symbol_id,
                timeframe=timeframe,
                source_id=source_id,
            ),
        )


def build_context_json(
    workspace_id: UUID,
    symbol_id: UUID,
    source_id: UUID | None,
    timeframe: str,
    state_version: str,
    data_quality_label: MarketMemoryDataQualityLabel,
    freshness_label: MarketMemoryFreshnessLabel,
    artifacts: MarketMemoryArtifacts,
) -> dict[str, object]:
    return to_json_value(
        {
            "identity": {
                "workspaceId": workspace_id,
                "symbolId": symbol_id,
                "sourceId": source_id,
                "timeframe": timeframe,
                "stateVersion": state_version,
            },
            "status": {
                "dataQualityLabel": data_quality_label.value,
                "freshnessLabel": freshness_label.value,
            },
            "latestFinalCandle": compact_candle(artifacts.latest_final_candle),
            "latestAnalysisRun": compact_analysis_run(artifacts.latest_analysis_run),
            "latestSignal": compact_signal(artifacts.latest_signal),
            "latestOutcome": compact_outcome(artifacts.latest_outcome),
            "featureSnapshot": compact_feature_snapshot(artifacts.feature_snapshot),
            "indicatorSnapshot": compact_indicator_snapshot(artifacts.indicator_snapshot),
            "advancedFeatureSnapshot": compact_advanced_feature_snapshot(
                artifacts.advanced_feature_snapshot
            ),
            "marketRegime": compact_market_regime(artifacts.market_regime),
            "marketSession": compact_market_session(artifacts.market_session),
            "multiTimeframeContext": compact_multi_timeframe_context(
                artifacts.multi_timeframe_context
            ),
            "crossAssetContext": compact_cross_asset_context(
                artifacts.cross_asset_context_run,
                artifacts.cross_asset_results,
            ),
            "dataQuality": compact_data_quality(artifacts.latest_data_quality_run),
            "policy": {
                "backendOnly": True,
                "deterministicArtifactsOnly": True,
                "noAnalysisExecution": True,
                "noOutcomeEvaluation": True,
                "noLlmClassification": True,
                "noSignalMutation": True,
                "noFinancialAdvice": True,
            },
        }
    )


def build_warnings_json(
    data_quality_label: MarketMemoryDataQualityLabel,
    freshness_label: MarketMemoryFreshnessLabel,
    artifacts: MarketMemoryArtifacts,
    max_warnings: int,
) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    add_warning(
        warnings,
        artifacts.latest_final_candle is None,
        "missing_final_candle",
        "high",
        "No final candle was available for the requested market memory identity",
    )
    add_warning(
        warnings,
        artifacts.latest_analysis_run is None,
        "missing_completed_analysis",
        "medium",
        "No completed analysis run was available",
    )
    add_warning(
        warnings,
        artifacts.latest_signal is None,
        "missing_signal",
        "medium",
        "No persisted signal was available",
    )
    add_warning(
        warnings,
        artifacts.feature_snapshot is None,
        "missing_feature_snapshot",
        "low",
        "No feature snapshot was available",
    )
    add_warning(
        warnings,
        artifacts.indicator_snapshot is None,
        "missing_indicator_snapshot",
        "low",
        "No indicator snapshot was available",
    )
    add_warning(
        warnings,
        artifacts.advanced_feature_snapshot is None,
        "missing_advanced_feature_snapshot",
        "low",
        "No advanced feature snapshot was available",
    )
    add_warning(
        warnings,
        artifacts.market_regime is None,
        "missing_market_regime",
        "low",
        "No market regime context was available",
    )
    add_warning(
        warnings,
        artifacts.market_session is None,
        "missing_market_session",
        "low",
        "No market session context was available",
    )
    add_warning(
        warnings,
        artifacts.multi_timeframe_context is None,
        "missing_multi_timeframe_context",
        "low",
        "No multi-timeframe context was available",
    )
    add_warning(
        warnings,
        artifacts.cross_asset_context_run is None,
        "missing_cross_asset_context",
        "low",
        "No cross-asset context was available",
    )
    add_warning(
        warnings,
        artifacts.latest_outcome is None,
        "missing_outcome",
        "low",
        "No persisted outcome was available",
    )
    add_warning(
        warnings,
        artifacts.latest_data_quality_run is None,
        "missing_data_quality_run",
        "low",
        "No persisted data quality run was available",
    )
    add_warning(
        warnings,
        freshness_label in {MarketMemoryFreshnessLabel.DELAYED, MarketMemoryFreshnessLabel.STALE},
        f"market_memory_{freshness_label.value}",
        "medium" if freshness_label == MarketMemoryFreshnessLabel.DELAYED else "high",
        f"Latest final candle freshness is {freshness_label.value}",
    )
    add_warning(
        warnings,
        data_quality_label
        in {
            MarketMemoryDataQualityLabel.DEGRADED,
            MarketMemoryDataQualityLabel.POOR,
            MarketMemoryDataQualityLabel.INSUFFICIENT,
        },
        f"data_quality_{data_quality_label.value}",
        "medium" if data_quality_label == MarketMemoryDataQualityLabel.DEGRADED else "high",
        f"Latest data quality label is {data_quality_label.value}",
    )
    if artifacts.latest_outcome is not None:
        add_warning(
            warnings,
            artifacts.latest_outcome.evaluation_status in {"insufficient_future_data", "failed"},
            f"outcome_{artifacts.latest_outcome.evaluation_status}",
            "medium",
            f"Latest outcome status is {artifacts.latest_outcome.evaluation_status}",
        )
    return warnings[:max_warnings]


def add_warning(
    warnings: list[dict[str, object]],
    condition: bool,
    code: str,
    severity: str,
    message: str,
) -> None:
    if condition:
        warnings.append({"code": code, "severity": severity, "message": message})


def determine_data_quality_label(
    data_quality_run: DataQualityRun | None,
    feature_snapshot: FeatureSnapshot | None,
) -> MarketMemoryDataQualityLabel:
    if data_quality_run is not None:
        return normalize_data_quality_label(data_quality_run.quality_label)
    feature_quality = nested_get(
        feature_snapshot.features_json if feature_snapshot else {},
        "dataQuality",
        "qualityScore",
    )
    if isinstance(feature_quality, int | float | Decimal | str):
        try:
            score = Decimal(str(feature_quality))
        except Exception:
            return MarketMemoryDataQualityLabel.UNKNOWN
        if score >= Decimal("0.95"):
            return MarketMemoryDataQualityLabel.STRONG
        if score >= Decimal("0.85"):
            return MarketMemoryDataQualityLabel.ACCEPTABLE
        if score >= Decimal("0.70"):
            return MarketMemoryDataQualityLabel.DEGRADED
        if score > Decimal("0"):
            return MarketMemoryDataQualityLabel.POOR
        return MarketMemoryDataQualityLabel.INSUFFICIENT
    return MarketMemoryDataQualityLabel.UNKNOWN


def normalize_data_quality_label(value: str | None) -> MarketMemoryDataQualityLabel:
    if value == "insufficient_data":
        return MarketMemoryDataQualityLabel.INSUFFICIENT
    try:
        return MarketMemoryDataQualityLabel(value or "unknown")
    except ValueError:
        return MarketMemoryDataQualityLabel.UNKNOWN


def derive_trend_state(artifacts: MarketMemoryArtifacts) -> str | None:
    if artifacts.market_regime is not None:
        return artifacts.market_regime.trend_regime
    if artifacts.latest_signal is not None and artifacts.latest_signal.trend_state is not None:
        return artifacts.latest_signal.trend_state
    return string_or_none(
        nested_get(
            artifacts.feature_snapshot.features_json if artifacts.feature_snapshot else {},
            "trend",
            "trendState",
        )
    )


def derive_volatility_state(artifacts: MarketMemoryArtifacts) -> str | None:
    if artifacts.market_regime is not None:
        return artifacts.market_regime.volatility_regime
    if artifacts.latest_signal is not None and artifacts.latest_signal.volatility_state is not None:
        return artifacts.latest_signal.volatility_state
    return string_or_none(
        nested_get(
            artifacts.feature_snapshot.features_json if artifacts.feature_snapshot else {},
            "volatility",
            "volatilityState",
        )
    )


def derive_range_state(artifacts: MarketMemoryArtifacts) -> str | None:
    if artifacts.market_regime is not None:
        return artifacts.market_regime.range_regime
    if artifacts.latest_signal is not None and artifacts.latest_signal.range_state is not None:
        return artifacts.latest_signal.range_state
    return string_or_none(
        nested_get(
            artifacts.feature_snapshot.features_json if artifacts.feature_snapshot else {},
            "range",
            "rangeState",
        )
    )


def derive_market_regime_label(market_regime: MarketRegimeContext | None) -> str | None:
    if market_regime is None:
        return None
    return "/".join(
        [
            market_regime.trend_regime,
            market_regime.volatility_regime,
            market_regime.range_regime,
        ]
    )


def derive_cross_asset_label(results: list[CrossAssetContextResult]) -> str | None:
    if not results:
        return None
    counts: dict[str, int] = {}
    for result in results:
        counts[result.alignment_label] = counts.get(result.alignment_label, 0) + 1
    return max(counts.items(), key=lambda item: item[1])[0]


def compact_candle(candle: Candle | None) -> dict[str, object] | None:
    if candle is None:
        return None
    return {
        "id": candle.id,
        "sourceId": candle.source_id,
        "timestamp": candle.timestamp,
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
        "isFinal": candle.is_final,
        "qualityScore": candle.quality_score,
    }


def compact_analysis_run(analysis_run: AnalysisRun | None) -> dict[str, object] | None:
    if analysis_run is None:
        return None
    return {
        "id": analysis_run.id,
        "sourceId": analysis_run.source_id,
        "analysisMode": analysis_run.analysis_mode,
        "status": analysis_run.status,
        "startTime": analysis_run.start_time,
        "endTime": analysis_run.end_time,
        "engineVersion": analysis_run.engine_version,
        "ruleSetVersion": analysis_run.rule_set_version,
        "completedAt": analysis_run.completed_at,
    }


def compact_signal(signal: Signal | None) -> dict[str, object] | None:
    if signal is None:
        return None
    return {
        "id": signal.id,
        "analysisRunId": signal.analysis_run_id,
        "bias": signal.bias,
        "patternType": signal.pattern_type,
        "classificationStatus": signal.classification_status,
        "confidenceScore": signal.confidence_score,
        "confidenceLabel": signal.confidence_label,
        "trendState": signal.trend_state,
        "volatilityState": signal.volatility_state,
        "rangeState": signal.range_state,
        "summary": signal.summary,
        "createdAt": signal.created_at,
    }


def compact_outcome(outcome: SignalOutcome | None) -> dict[str, object] | None:
    if outcome is None:
        return None
    return {
        "id": outcome.id,
        "signalId": outcome.signal_id,
        "horizonMinutes": outcome.horizon_minutes,
        "evaluationStatus": outcome.evaluation_status,
        "outcomeLabel": outcome.outcome_label,
        "futureCandleCount": outcome.future_candle_count,
        "directionFollowed": outcome.direction_followed,
        "reversalDetected": outcome.reversal_detected,
        "movementQuality": outcome.movement_quality,
        "evaluationVersion": outcome.evaluation_version,
        "createdAt": outcome.created_at,
    }


def compact_feature_snapshot(snapshot: FeatureSnapshot | None) -> dict[str, object] | None:
    if snapshot is None:
        return None
    features = snapshot.features_json
    return {
        "id": snapshot.id,
        "analysisRunId": snapshot.analysis_run_id,
        "startTime": snapshot.start_time,
        "endTime": snapshot.end_time,
        "movement": select_keys(
            features.get("movement"),
            ["netDirection", "percentageMove", "movementEfficiency"],
        ),
        "range": select_keys(
            features.get("range"),
            ["rangeState", "currentRangeHigh", "currentRangeLow"],
        ),
        "volatility": select_keys(
            features.get("volatility"),
            ["volatilityState", "atrExpansionRatio"],
        ),
        "trend": select_keys(features.get("trend"), ["trendState", "trendSlope"]),
        "dataQuality": features.get("dataQuality"),
        "createdAt": snapshot.created_at,
    }


def compact_indicator_snapshot(snapshot: IndicatorSnapshot | None) -> dict[str, object] | None:
    if snapshot is None:
        return None
    indicators = snapshot.indicators_json
    return {
        "id": snapshot.id,
        "analysisRunId": snapshot.analysis_run_id,
        "readiness": select_keys(
            indicators.get("calculation"),
            ["isReady", "analysisCandleCount", "inputCandleCount"],
        ),
        "ema": select_keys(indicators.get("ema"), ["state", "isReady"]),
        "rsi": select_keys(indicators.get("rsi"), ["state", "isReady"]),
        "macd": select_keys(indicators.get("macd"), ["state", "isReady"]),
        "atr": select_keys(indicators.get("atr"), ["state", "isReady"]),
        "createdAt": snapshot.created_at,
    }


def compact_advanced_feature_snapshot(
    snapshot: AdvancedFeatureSnapshot | None,
) -> dict[str, object] | None:
    if snapshot is None:
        return None
    return {
        "id": snapshot.id,
        "analysisRunId": snapshot.analysis_run_id,
        "featurePackVersion": snapshot.feature_pack_version,
        "summary": snapshot.summary,
        "impulse": compact_group(snapshot.impulse_json),
        "correction": compact_group(snapshot.correction_json),
        "wickPressure": compact_group(snapshot.wick_pressure_json),
        "movementEfficiency": compact_group(snapshot.movement_efficiency_json),
        "compressionExpansion": compact_group(snapshot.compression_expansion_json),
        "swingStructure": compact_group(snapshot.swing_structure_json),
        "exhaustion": compact_group(snapshot.exhaustion_json),
        "liquiditySweep": compact_group(snapshot.liquidity_sweep_json),
        "warningCount": len(snapshot.warnings_json),
        "createdAt": snapshot.created_at,
    }


def compact_market_regime(context: MarketRegimeContext | None) -> dict[str, object] | None:
    if context is None:
        return None
    return {
        "id": context.id,
        "analysisRunId": context.analysis_run_id,
        "signalId": context.signal_id,
        "trendRegime": context.trend_regime,
        "volatilityRegime": context.volatility_regime,
        "rangeRegime": context.range_regime,
        "dataQualityLabel": context.data_quality_label,
        "confidenceLabel": context.confidence_label,
        "summary": context.summary,
        "createdAt": context.created_at,
    }


def compact_market_session(context: MarketSessionContext | None) -> dict[str, object] | None:
    if context is None:
        return None
    return {
        "id": context.id,
        "analysisRunId": context.analysis_run_id,
        "signalId": context.signal_id,
        "contextTime": context.context_time,
        "timezoneName": context.timezone_name,
        "sessionLabel": context.session_label,
        "confidenceScore": context.confidence_score,
        "createdAt": context.created_at,
    }


def compact_multi_timeframe_context(
    context: MultiTimeframeContext | None,
) -> dict[str, object] | None:
    if context is None:
        return None
    return {
        "id": context.id,
        "analysisRunId": context.analysis_run_id,
        "signalId": context.signal_id,
        "contextTimeframes": context.context_timeframes_json,
        "trendAlignment": context.trend_alignment,
        "volatilityAlignment": context.volatility_alignment,
        "rangeAlignment": context.range_alignment,
        "agreementScore": context.agreement_score,
        "agreementLabel": context.agreement_label,
        "contextSummary": context.context_summary,
        "warningCount": len(context.warnings_json),
        "createdAt": context.created_at,
    }


def compact_cross_asset_context(
    run: CrossAssetContextRun | None,
    results: list[CrossAssetContextResult],
) -> dict[str, object] | None:
    if run is None:
        return None
    return {
        "id": run.id,
        "analysisRunId": run.analysis_run_id,
        "signalId": run.signal_id,
        "status": run.status,
        "contextVersion": run.context_version,
        "comparedSymbolCount": run.compared_symbol_count,
        "resultCount": run.result_count,
        "alignmentLabel": derive_cross_asset_label(results),
        "results": [
            {
                "id": result.id,
                "comparedSymbolId": result.compared_symbol_id,
                "alignmentLabel": result.alignment_label,
                "leadLagLabel": result.lead_lag_label,
                "dataQualityLabel": result.data_quality_label,
            }
            for result in results[:10]
        ],
        "summary": run.summary,
        "createdAt": run.created_at,
    }


def compact_data_quality(run: DataQualityRun | None) -> dict[str, object] | None:
    if run is None:
        return None
    return {
        "id": run.id,
        "scopeType": run.scope_type,
        "status": run.status,
        "qualityVersion": run.quality_version,
        "qualityScore": run.quality_score,
        "qualityLabel": normalize_data_quality_label(run.quality_label).value,
        "candleCount": run.candle_count,
        "findingCount": run.finding_count,
        "createdAt": run.created_at,
    }


def compact_group(value: dict[str, object]) -> dict[str, object]:
    return {
        key: item
        for key, item in value.items()
        if key.endswith("Label")
        or key.endswith("State")
        or key.endswith("Direction")
        or key.endswith("Score")
        or key in {"isReady", "warning", "warnings"}
    }


def select_keys(value: object, keys: list[str]) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {key: value[key] for key in keys if key in value}


def nested_get(value: dict[str, object], first_key: str, second_key: str) -> object | None:
    first_value = value.get(first_key)
    if not isinstance(first_value, dict):
        return None
    return first_value.get(second_key)


def string_or_none(value: object | None) -> str | None:
    return value if isinstance(value, str) else None


def to_json_value(value: object) -> JsonValue:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_json_value(item) for item in value]
    return value
