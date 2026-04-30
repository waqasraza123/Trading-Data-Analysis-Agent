from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.analysis.models import AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.explanations.models import DeterministicExplanation
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.llm_explanations.input_builder import json_safe
from app.modules.news.models import NewsEvent, SignalNewsCorrelation
from app.modules.outcomes.models import SignalOutcome
from app.modules.outcomes.repository import OutcomeRepository
from app.modules.reasoning.schemas import ScenarioReasoningInputSnapshot
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)
from app.modules.symbols.models import Symbol

MAX_CONFIDENCE_COMPONENTS = 12
MAX_EVIDENCE = 16
MAX_RISK_NOTES = 12
MAX_NEWS_CORRELATIONS = 8
MAX_SIGNAL_OUTCOMES = 8
MAX_OUTCOME_HISTORY_ROWS = 80
MAX_FEATURE_KEYS = 16
MAX_INDICATOR_KEYS = 16


class ScenarioReasoningInputBuilder:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.outcome_repository = OutcomeRepository(session)

    async def build_signal_input(
        self,
        signal: Signal,
        run: AnalysisRun,
        symbol: Symbol,
        confidence_components: list[SignalConfidenceComponent],
        evidence: list[SignalEvidence],
        risk_notes: list[SignalRiskNote],
        deterministic_explanation: DeterministicExplanation | None,
        feature_snapshot: FeatureSnapshot | None,
        indicator_snapshot: IndicatorSnapshot | None,
        news_correlations: list[dict[str, object]],
        horizons_minutes: list[int],
    ) -> ScenarioReasoningInputSnapshot:
        latest_outcomes = await self.outcome_repository.list_by_signal_id(signal.id)
        outcome_history = await self.build_outcome_history(signal, horizons_minutes)
        screenshot_metadata = await self.build_screenshot_metadata(run.id)
        truncation: dict[str, int] = {}
        confidence_items = bounded(
            confidence_components,
            MAX_CONFIDENCE_COMPONENTS,
            serialize_confidence_component,
            truncation,
            "confidenceComponents",
        )
        evidence_items = bounded(
            evidence,
            MAX_EVIDENCE,
            serialize_signal_evidence,
            truncation,
            "signalEvidence",
        )
        risk_items = bounded(
            risk_notes,
            MAX_RISK_NOTES,
            serialize_risk_note,
            truncation,
            "riskNotes",
        )
        news_items = bounded_values(
            news_correlations,
            MAX_NEWS_CORRELATIONS,
            truncation,
            "newsCorrelations",
        )
        outcome_items = bounded(
            latest_outcomes,
            MAX_SIGNAL_OUTCOMES,
            serialize_outcome,
            truncation,
            "latestSignalOutcomes",
        )
        return ScenarioReasoningInputSnapshot(
            signal_id=signal.id,
            analysis_run_id=run.id,
            workspace_id=signal.workspace_id,
            symbol_id=signal.symbol_id,
            symbol=symbol.symbol,
            timeframe=signal.timeframe,
            analysis_window={
                "startTime": run.start_time.isoformat(),
                "endTime": run.end_time.isoformat(),
            },
            classification_status=signal.classification_status,
            bias=signal.bias,
            pattern_type=signal.pattern_type,
            strategy_profile_key=signal.strategy_profile_key,
            strategy_profile_version=signal.strategy_profile_version,
            confidence_score=decimal_to_text(signal.confidence_score),
            confidence_label=signal.confidence_label,
            signal_summary=signal.summary,
            no_signal_reason=signal.no_signal_reason,
            confidence_components=confidence_items,
            signal_evidence=evidence_items,
            risk_notes=risk_items,
            deterministic_explanation=serialize_deterministic_explanation(
                deterministic_explanation
            ),
            news_correlations=news_items,
            latest_signal_outcomes=outcome_items,
            outcome_history=outcome_history,
            feature_summary=snapshot_summary(feature_snapshot, "features_json", MAX_FEATURE_KEYS),
            indicator_summary=snapshot_summary(
                indicator_snapshot,
                "indicators_json",
                MAX_INDICATOR_KEYS,
            ),
            replay_metadata=serialize_replay_metadata(run),
            screenshot_decision_metadata=screenshot_metadata,
            truncation=truncation,
        )

    async def build_outcome_history(
        self,
        signal: Signal,
        horizons_minutes: list[int],
    ) -> dict[str, object]:
        items: list[dict[str, object]] = []
        total_considered = 0
        for horizon in horizons_minutes:
            outcomes = await self.outcome_repository.list_filtered_outcomes(
                workspace_id=signal.workspace_id,
                horizon_minutes=horizon,
                symbol_id=signal.symbol_id,
                timeframe=signal.timeframe,
                pattern_type=signal.pattern_type,
                strategy_profile_key=signal.strategy_profile_key,
            )
            total_considered += len(outcomes)
            bounded_outcomes = outcomes[:MAX_OUTCOME_HISTORY_ROWS]
            label_counts = Counter(outcome.outcome_label for outcome in bounded_outcomes)
            status_counts = Counter(outcome.evaluation_status for outcome in bounded_outcomes)
            items.append(
                {
                    "horizonMinutes": horizon,
                    "matchingOutcomeCount": len(outcomes),
                    "includedOutcomeCount": len(bounded_outcomes),
                    "outcomeLabelCounts": dict(sorted(label_counts.items())),
                    "evaluationStatusCounts": dict(sorted(status_counts.items())),
                }
            )
        return {
            "filters": {
                "strategyProfileKey": signal.strategy_profile_key,
                "patternType": signal.pattern_type,
                "symbolId": str(signal.symbol_id),
                "timeframe": signal.timeframe,
            },
            "items": items,
            "totalMatchingOutcomeCount": total_considered,
            "truncatedPerHorizonLimit": MAX_OUTCOME_HISTORY_ROWS,
        }

    async def build_screenshot_metadata(self, analysis_run_id: UUID) -> dict[str, object] | None:
        statement: Select[tuple[ChartScreenshotRun]] = (
            select(ChartScreenshotRun)
            .where(ChartScreenshotRun.analysis_run_id == analysis_run_id)
            .order_by(ChartScreenshotRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        screenshot_run = result.scalar_one_or_none()
        if screenshot_run is None:
            return None
        return {
            "chartScreenshotRunId": str(screenshot_run.id),
            "status": screenshot_run.status,
            "analysisHypothesis": screenshot_run.analysis_hypothesis,
            "analysisHypothesisConfidence": optional_decimal(
                screenshot_run.analysis_hypothesis_confidence
            ),
            "extractionConfidence": decimal_to_text(screenshot_run.extraction_confidence),
            "storedCandleCount": screenshot_run.stored_candle_count,
            "conflictCount": screenshot_run.conflict_count,
            "duplicateCount": screenshot_run.duplicate_count,
        }


def build_news_correlation_payload(
    correlations: list[SignalNewsCorrelation],
    events: list[NewsEvent],
) -> list[dict[str, object]]:
    events_by_id = {event.id: event for event in events}
    payload: list[dict[str, object]] = []
    for correlation in correlations:
        event = events_by_id.get(correlation.news_event_id)
        if event is None:
            continue
        payload.append(
            {
                "eventTitle": event.title,
                "eventType": event.event_type,
                "eventTime": event.event_time.isoformat(),
                "currency": event.currency,
                "asset": event.asset,
                "importance": event.importance,
                "correlationLabel": correlation.correlation_label,
                "correlationScore": decimal_to_text(correlation.correlation_score),
                "timeDeltaMinutes": decimal_to_text(correlation.time_delta_minutes),
                "directionAlignment": correlation.direction_alignment,
                "volatilityReaction": correlation.volatility_reaction,
                "reason": correlation.reason,
            }
        )
    return payload


def bounded[T](
    items: Sequence[T],
    limit: int,
    serializer: Callable[[T], dict[str, object]],
    truncation: dict[str, int],
    key: str,
) -> list[dict[str, object]]:
    if len(items) > limit:
        truncation[key] = len(items) - limit
    return [serializer(item) for item in items[:limit]]


def bounded_values(
    items: list[dict[str, object]],
    limit: int,
    truncation: dict[str, int],
    key: str,
) -> list[dict[str, object]]:
    if len(items) > limit:
        truncation[key] = len(items) - limit
    return items[:limit]


def serialize_confidence_component(item: SignalConfidenceComponent) -> dict[str, object]:
    return {
        "componentName": item.component_name,
        "componentScore": decimal_to_text(item.component_score),
        "componentWeight": decimal_to_text(item.component_weight),
        "weightedScore": decimal_to_text(item.weighted_score),
        "reason": item.reason,
    }


def serialize_signal_evidence(item: SignalEvidence) -> dict[str, object]:
    return {
        "evidenceType": item.evidence_type,
        "direction": item.direction,
        "message": item.message,
        "numericValue": optional_decimal(item.numeric_value),
        "weight": decimal_to_text(item.weight),
        "metadata": json_safe(item.metadata_json),
    }


def serialize_risk_note(item: SignalRiskNote) -> dict[str, object]:
    return {
        "code": item.code,
        "message": item.message,
        "severity": item.severity,
        "metadata": json_safe(item.metadata_json),
    }


def serialize_outcome(outcome: SignalOutcome) -> dict[str, object]:
    return {
        "outcomeId": str(outcome.id),
        "horizonMinutes": outcome.horizon_minutes,
        "evaluationStatus": outcome.evaluation_status,
        "outcomeLabel": outcome.outcome_label,
        "futureCandleCount": outcome.future_candle_count,
        "directionFollowed": outcome.direction_followed,
        "reversalDetected": outcome.reversal_detected,
        "movementQuality": outcome.movement_quality,
        "referenceTime": outcome.reference_time.isoformat(),
    }


def serialize_deterministic_explanation(
    explanation: DeterministicExplanation | None,
) -> dict[str, object] | None:
    if explanation is None:
        return None
    return {
        "id": str(explanation.id),
        "templateVersion": explanation.template_version,
        "explanationType": explanation.explanation_type,
        "shortSummary": explanation.short_summary,
        "marketBehavior": explanation.market_behavior,
        "evidenceSummary": explanation.evidence_summary,
        "confidenceSummary": explanation.confidence_summary,
        "riskSummary": explanation.risk_summary,
        "noSignalSummary": explanation.no_signal_summary,
        "safetyStatus": explanation.safety_status,
    }


def snapshot_summary(
    snapshot: FeatureSnapshot | IndicatorSnapshot | None,
    payload_attr: str,
    limit: int,
) -> dict[str, object] | None:
    if snapshot is None:
        return None
    payload = getattr(snapshot, payload_attr)
    if not isinstance(payload, dict):
        raise AppError(500, "invalid_snapshot_payload", "Snapshot payload was invalid")
    keys = sorted(str(key) for key in payload)
    included_keys = keys[:limit]
    return {
        "id": str(snapshot.id),
        "includedKeys": included_keys,
        "truncatedKeyCount": max(0, len(keys) - limit),
        "data": {key: json_safe(payload[key]) for key in included_keys},
    }


def serialize_replay_metadata(run: AnalysisRun) -> dict[str, object] | None:
    if run.replayed_from_analysis_run_id is None and run.analysis_mode != "replay":
        return None
    return {
        "analysisMode": run.analysis_mode,
        "replayedFromAnalysisRunId": (
            str(run.replayed_from_analysis_run_id)
            if run.replayed_from_analysis_run_id is not None
            else None
        ),
        "replayMode": run.replay_mode,
        "engineVersion": run.engine_version,
        "ruleSetVersion": run.rule_set_version,
    }


def optional_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return decimal_to_text(value)


def decimal_to_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(int(normalized))
    return format(normalized, "f")


def iso_datetime(value: datetime) -> str:
    return value.isoformat()
