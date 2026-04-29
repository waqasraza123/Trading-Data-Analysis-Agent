from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.analysis.models import AnalysisRun
from app.modules.explanations.models import DeterministicExplanation
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.llm_explanations.schemas import LlmExplanationInputPayload
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)


def build_llm_input_payload(
    signal: Signal,
    run: AnalysisRun,
    symbol: str,
    confidence_components: list[SignalConfidenceComponent],
    evidence: list[SignalEvidence],
    risk_notes: list[SignalRiskNote],
    deterministic_explanation: DeterministicExplanation | None,
    feature_snapshot: FeatureSnapshot | None,
    indicator_snapshot: IndicatorSnapshot | None,
    news_correlations: list[dict[str, object]],
) -> LlmExplanationInputPayload:
    return LlmExplanationInputPayload(
        signal_id=signal.id,
        analysis_run_id=run.id,
        workspace_id=signal.workspace_id,
        symbol=symbol,
        timeframe=signal.timeframe,
        analysis_window={
            "start_time": _to_iso_datetime(run.start_time),
            "end_time": _to_iso_datetime(run.end_time),
        },
        classification_status=signal.classification_status,
        bias=signal.bias,
        pattern_type=signal.pattern_type,
        strategy_profile_key=signal.strategy_profile_key,
        strategy_profile_version=signal.strategy_profile_version,
        strategy_profile_snapshot=json_safe_optional_mapping(signal.strategy_profile_snapshot_json),
        feature_snapshot=snapshot_payload(
            feature_snapshot.id if feature_snapshot is not None else None,
            feature_snapshot.features_json if feature_snapshot is not None else None,
        ),
        indicator_snapshot=snapshot_payload(
            indicator_snapshot.id if indicator_snapshot is not None else None,
            indicator_snapshot.indicators_json if indicator_snapshot is not None else None,
        ),
        confidence={
            "score": _decimal_to_text(signal.confidence_score),
            "label": signal.confidence_label,
            "candidate_strength": _optional_decimal(signal.candidate_strength),
        },
        confidence_components=[
            {
                "component_name": item.component_name,
                "component_score": _decimal_to_text(item.component_score),
                "component_weight": _decimal_to_text(item.component_weight),
                "weighted_score": _decimal_to_text(item.weighted_score),
                "reason": item.reason,
            }
            for item in confidence_components
        ],
        evidence=[
            {
                "evidence_type": item.evidence_type,
                "direction": item.direction,
                "message": item.message,
                "numeric_value": _optional_decimal(item.numeric_value),
                "weight": _decimal_to_text(item.weight),
            }
            for item in evidence
        ],
        risk_notes=[
            {
                "code": item.code,
                "message": item.message,
                "severity": item.severity,
                "metadata": item.metadata_json,
            }
            for item in risk_notes
        ],
        deterministic_explanation=(
            {
                "text": deterministic_explanation.full_text,
                "template_version": deterministic_explanation.template_version,
                "safety_status": deterministic_explanation.safety_status,
                "source_snapshot": deterministic_explanation.source_snapshot_json,
            }
            if deterministic_explanation is not None
            else None
        ),
        movement_fields={
            "pips_moved": _optional_decimal(signal.pips_moved),
            "tick_moved": _optional_decimal(signal.tick_moved),
            "movement_direction": signal.movement_direction,
            "movement_quality": signal.movement_quality,
        },
        trend_state=signal.trend_state,
        volatility_state=signal.volatility_state,
        range_state=signal.range_state,
        no_signal_reason=signal.no_signal_reason,
        news_correlations=news_correlations,
    )


def _optional_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _decimal_to_text(value)


def _decimal_to_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(int(normalized))
    return format(normalized, "f")


def _to_iso_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        return value.isoformat()
    return value.isoformat()


def snapshot_payload(
    snapshot_id: UUID | None,
    payload: Mapping[str, object] | None,
) -> dict[str, object] | None:
    if snapshot_id is None or payload is None:
        return None
    return {
        "id": str(snapshot_id),
        "data": json_safe(payload),
    }


def json_safe_optional_mapping(value: Mapping[str, object] | None) -> dict[str, object] | None:
    if value is None:
        return None
    safe_value = json_safe(value)
    return safe_value if isinstance(safe_value, dict) else None


def json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return _decimal_to_text(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return _to_iso_datetime(value)
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [json_safe(item) for item in value]
    return value
