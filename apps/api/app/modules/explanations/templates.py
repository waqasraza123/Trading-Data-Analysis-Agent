from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from app.modules.explanations.models import ExplanationType
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.signals.models import (
    Signal,
    SignalClassificationStatus,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)

TEMPLATE_VERSION = "deterministic_v1"
FALLBACK_EXPLANATION = (
    "A deterministic analysis result was generated, but the detailed explanation was "
    "replaced by a safety fallback. Review the structured signal, evidence, confidence "
    "components, and risk notes."
)

NO_SIGNAL_REASON_MESSAGES: dict[str, str] = {
    "no_pattern_candidates": (
        "No signal was generated because no pattern candidates were available for this "
        "analysis run."
    ),
    "no_profile_candidates": (
        "No signal was generated because no pattern candidate matched an active strategy "
        "profile."
    ),
    "below_minimum_strength": (
        "No signal was generated because available candidates were below the configured "
        "strength threshold."
    ),
    "below_minimum_confidence": (
        "No signal was generated because confidence was below the configured threshold."
    ),
    "conflicting_directional_candidates": (
        "No clear signal was generated because opposing directional candidates were too "
        "close in strength."
    ),
    "fakeout_risk": (
        "No breakout signal was generated because fakeout risk was too close to or "
        "stronger than the directional candidate."
    ),
    "chop_or_sideways_market": (
        "No directional signal was generated because sideways or choppy market conditions "
        "were stronger than directional candidates."
    ),
    "low_data_quality": (
        "No signal was generated because candle data quality was below the configured "
        "threshold."
    ),
    "insufficient_evidence": (
        "No signal was generated because the available evidence was not strong enough for "
        "deterministic classification."
    ),
    "missing_feature_snapshot": (
        "No signal was generated because required feature snapshot data was unavailable."
    ),
    "missing_indicator_snapshot": (
        "The signal was generated with degraded confidence because indicator snapshot data "
        "was unavailable."
    ),
    "unsupported_pattern_type": (
        "No signal was generated because the selected pattern type is not supported by the "
        "active deterministic profiles."
    ),
}
UNKNOWN_NO_SIGNAL_MESSAGE = (
    "No signal was generated because deterministic classification did not find enough "
    "clean evidence."
)


@dataclass(frozen=True)
class ExplanationDraft:
    template_version: str
    explanation_type: ExplanationType
    short_summary: str
    market_behavior: str
    evidence_summary: str
    confidence_summary: str
    risk_summary: str
    no_signal_summary: str | None
    full_text: str
    source_snapshot_json: dict[str, object]


def build_explanation_draft(
    signal: Signal,
    confidence_components: list[SignalConfidenceComponent],
    evidence: list[SignalEvidence],
    risk_notes: list[SignalRiskNote],
    feature_snapshot: FeatureSnapshot | None,
    indicator_snapshot: IndicatorSnapshot | None,
) -> ExplanationDraft:
    short_summary = build_short_summary(signal)
    market_behavior = build_market_behavior(signal)
    evidence_summary = build_evidence_summary(evidence)
    confidence_summary = build_confidence_summary(signal, confidence_components)
    risk_summary = build_risk_summary(risk_notes)
    no_signal_summary = build_no_signal_summary(signal)
    full_text = build_full_text(
        short_summary=short_summary,
        market_behavior=market_behavior,
        evidence_summary=evidence_summary,
        confidence_summary=confidence_summary,
        risk_summary=risk_summary,
        no_signal_summary=no_signal_summary,
    )
    return ExplanationDraft(
        template_version=TEMPLATE_VERSION,
        explanation_type=resolve_explanation_type(signal),
        short_summary=short_summary,
        market_behavior=market_behavior,
        evidence_summary=evidence_summary,
        confidence_summary=confidence_summary,
        risk_summary=risk_summary,
        no_signal_summary=no_signal_summary,
        full_text=full_text,
        source_snapshot_json=build_source_snapshot(
            signal=signal,
            confidence_components=confidence_components,
            evidence=evidence,
            risk_notes=risk_notes,
            feature_snapshot=feature_snapshot,
            indicator_snapshot=indicator_snapshot,
        ),
    )


def build_short_summary(signal: Signal) -> str:
    status = signal.classification_status
    if status == SignalClassificationStatus.SIGNAL:
        profile = signal.strategy_profile_key or "deterministic"
        return f"The signal was classified as {signal.bias} by the {profile} profile."
    if status == SignalClassificationStatus.UNCLEAR:
        return (
            "The analysis result is unclear because deterministic classification found "
            "mixed or conflicting evidence."
        )
    if status == SignalClassificationStatus.INSUFFICIENT_EVIDENCE:
        return build_no_signal_reason_message(signal.no_signal_reason)
    return build_no_signal_reason_message(signal.no_signal_reason)


def build_market_behavior(signal: Signal) -> str:
    details = [f"Bias was {signal.bias}."]
    if signal.pattern_type is not None:
        details.append(f"Pattern type was {signal.pattern_type}.")
    if signal.movement_direction is not None:
        details.append(f"Movement direction was {signal.movement_direction}.")
    if signal.pips_moved is not None:
        details.append(f"Recorded movement was {format_decimal(signal.pips_moved)} pips.")
    if signal.tick_moved is not None:
        details.append(f"Recorded movement was {format_decimal(signal.tick_moved)} ticks.")
    if signal.volatility_state is not None:
        details.append(f"Volatility state was {signal.volatility_state}.")
    if signal.trend_state is not None:
        details.append(f"Trend state was {signal.trend_state}.")
    if signal.range_state is not None:
        details.append(f"Range state was {signal.range_state}.")
    if signal.movement_quality is not None:
        details.append(f"Movement quality was {signal.movement_quality}.")
    if len(details) == 1:
        details.append("No additional deterministic market behavior fields were attached.")
    return " ".join(details)


def build_evidence_summary(evidence: list[SignalEvidence]) -> str:
    if not evidence:
        return "No persisted signal evidence rows were attached to this signal."
    visible_evidence = evidence[:6]
    entries = [
        f"{item.message} Direction: {item.direction}. Weight: {format_decimal(item.weight)}."
        for item in visible_evidence
    ]
    if len(evidence) > len(visible_evidence):
        entries.append(f"{len(evidence) - len(visible_evidence)} additional evidence rows exist.")
    return "Persisted evidence included: " + " ".join(entries)


def build_confidence_summary(
    signal: Signal,
    confidence_components: list[SignalConfidenceComponent],
) -> str:
    base = (
        f"Confidence score was {format_decimal(signal.confidence_score)} with label "
        f"{signal.confidence_label}."
    )
    if not confidence_components:
        return base + " No persisted confidence components were attached to this signal."
    ordered = sorted(
        confidence_components,
        key=lambda component: component.weighted_score,
        reverse=True,
    )
    strongest = ordered[:2]
    weakest = list(reversed(ordered[-2:]))
    strongest_text = ", ".join(
        f"{component.component_name} ({format_decimal(component.component_score)})"
        for component in strongest
    )
    weakest_text = ", ".join(
        f"{component.component_name} ({format_decimal(component.component_score)})"
        for component in weakest
    )
    parts = [
        base,
        f"Strongest components were {strongest_text}.",
        f"Weakest components were {weakest_text}.",
    ]
    data_quality = next(
        (
            component
            for component in confidence_components
            if component.component_name == "data_quality"
        ),
        None,
    )
    if data_quality is not None:
        parts.append(f"Data quality impact: {data_quality.reason}")
    return " ".join(parts)


def build_risk_summary(risk_notes: list[SignalRiskNote]) -> str:
    if not risk_notes:
        return "No additional deterministic risk notes were attached to this signal."
    visible_notes = risk_notes[:6]
    entries = [
        f"{note.message} Severity: {note.severity}. Code: {note.code}."
        for note in visible_notes
    ]
    if len(risk_notes) > len(visible_notes):
        entries.append(f"{len(risk_notes) - len(visible_notes)} additional risk notes exist.")
    return "Risk notes attached: " + " ".join(entries)


def build_no_signal_summary(signal: Signal) -> str | None:
    if signal.classification_status not in {
        SignalClassificationStatus.NO_SIGNAL,
        SignalClassificationStatus.UNCLEAR,
        SignalClassificationStatus.INSUFFICIENT_EVIDENCE,
    }:
        return None
    return build_no_signal_reason_message(signal.no_signal_reason)


def build_no_signal_reason_message(reason: str | None) -> str:
    if reason is None:
        return UNKNOWN_NO_SIGNAL_MESSAGE
    return NO_SIGNAL_REASON_MESSAGES.get(reason, UNKNOWN_NO_SIGNAL_MESSAGE)


def build_full_text(
    short_summary: str,
    market_behavior: str,
    evidence_summary: str,
    confidence_summary: str,
    risk_summary: str,
    no_signal_summary: str | None,
) -> str:
    sections = [
        f"Summary: {short_summary}",
        f"Market behavior: {market_behavior}",
        f"Evidence: {evidence_summary}",
        f"Confidence: {confidence_summary}",
        f"Risk: {risk_summary}",
    ]
    if no_signal_summary is not None:
        sections.append(f"No-signal context: {no_signal_summary}")
    sections.append(
        "This is deterministic analysis based on available candle data and is not a "
        "trade instruction."
    )
    return "\n\n".join(sections)


def resolve_explanation_type(signal: Signal) -> ExplanationType:
    if signal.classification_status == SignalClassificationStatus.SIGNAL:
        return ExplanationType.DETERMINISTIC_SIGNAL
    return ExplanationType.DETERMINISTIC_NO_SIGNAL


def build_source_snapshot(
    signal: Signal,
    confidence_components: list[SignalConfidenceComponent],
    evidence: list[SignalEvidence],
    risk_notes: list[SignalRiskNote],
    feature_snapshot: FeatureSnapshot | None,
    indicator_snapshot: IndicatorSnapshot | None,
) -> dict[str, object]:
    return cast(
        dict[str, object],
        json_safe(
                {
                    "signal": {
                        "id": signal.id,
                        "analysisRunId": signal.analysis_run_id,
                        "workspaceId": signal.workspace_id,
                        "symbolId": signal.symbol_id,
                        "timeframe": signal.timeframe,
                        "classificationStatus": signal.classification_status,
                        "bias": signal.bias,
                        "patternType": signal.pattern_type,
                        "confidenceScore": signal.confidence_score,
                        "confidenceLabel": signal.confidence_label,
                        "candidateStrength": signal.candidate_strength,
                        "selectedPatternCandidateId": signal.selected_pattern_candidate_id,
                        "pipsMoved": signal.pips_moved,
                        "tickMoved": signal.tick_moved,
                        "movementDirection": signal.movement_direction,
                        "movementQuality": signal.movement_quality,
                        "volatilityState": signal.volatility_state,
                        "trendState": signal.trend_state,
                        "rangeState": signal.range_state,
                        "noSignalReason": signal.no_signal_reason,
                    },
                    "strategyProfile": signal.strategy_profile_snapshot_json,
                    "featureSnapshot": snapshot_payload(
                        feature_snapshot.id if feature_snapshot is not None else None,
                        feature_snapshot.features_json if feature_snapshot is not None else None,
                    ),
                    "indicatorSnapshot": snapshot_payload(
                        indicator_snapshot.id if indicator_snapshot is not None else None,
                        (
                            indicator_snapshot.indicators_json
                            if indicator_snapshot is not None
                            else None
                        ),
                    ),
                    "confidenceComponents": [
                        {
                            "componentName": component.component_name,
                            "componentScore": component.component_score,
                            "componentWeight": component.component_weight,
                            "weightedScore": component.weighted_score,
                            "reason": component.reason,
                        }
                        for component in confidence_components
                    ],
                    "evidence": [
                        {
                            "evidenceType": item.evidence_type,
                            "direction": item.direction,
                            "message": item.message,
                            "numericValue": item.numeric_value,
                            "weight": item.weight,
                            "metadata": item.metadata_json,
                        }
                        for item in evidence
                    ],
                    "riskNotes": [
                        {
                            "code": note.code,
                            "message": note.message,
                            "severity": note.severity,
                            "metadata": note.metadata_json,
                        }
                        for note in risk_notes
                    ],
                },
        ),
    )


def snapshot_payload(snapshot_id: UUID | None, payload: Mapping[str, object] | None) -> object:
    if snapshot_id is None or payload is None:
        return None
    return {"id": snapshot_id, "data": payload}


def json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [json_safe(item) for item in value]
    return value


def format_decimal(value: Decimal) -> str:
    return format(value.normalize(), "f")
