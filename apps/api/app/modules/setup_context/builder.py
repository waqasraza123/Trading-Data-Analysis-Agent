from dataclasses import dataclass
from decimal import Decimal

from app.config import Settings
from app.modules.advanced_features.models import AdvancedFeatureSnapshot
from app.modules.analysis.models import AnalysisRun
from app.modules.candles.models import Candle
from app.modules.cross_asset_context.models import CrossAssetContextResult, CrossAssetContextRun
from app.modules.data_quality.models import DataQualityRun
from app.modules.decision_readiness.models import DecisionReadinessAssessment
from app.modules.features.models import FeatureSnapshot
from app.modules.market_regimes.models import MarketRegimeContext
from app.modules.market_sessions.models import MarketSessionContext
from app.modules.outcomes.models import SignalOutcome
from app.modules.patterns.models import PatternCandidate
from app.modules.setup_context.models import (
    SetupContext,
    SetupContextDirectionalBias,
    SetupContextStatus,
    SetupQualityLabel,
)
from app.modules.setup_context.zones import (
    build_invalidation_context,
    build_observation_zones,
    build_target_context_zones,
)
from app.modules.signals.models import (
    Signal,
    SignalClassificationStatus,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)
from app.modules.timeframe_aggregation.models import MultiTimeframeContext

ZERO = Decimal("0")
ONE = Decimal("1")
FOUR_PLACES = Decimal("0.0001")
RISK_PENALTIES = {
    "info": Decimal("0.00"),
    "low": Decimal("0.08"),
    "medium": Decimal("0.20"),
    "high": Decimal("0.38"),
    "critical": Decimal("0.65"),
}
QUALITY_COMPONENT_WEIGHTS = {
    "confidence": Decimal("0.25"),
    "evidence_alignment": Decimal("0.18"),
    "risk_notes": Decimal("0.15"),
    "market_regime": Decimal("0.10"),
    "multi_timeframe": Decimal("0.10"),
    "data_quality": Decimal("0.12"),
    "outcome_context": Decimal("0.05"),
    "readiness_context": Decimal("0.05"),
}
ALLOWED_NEXT_OBSERVATIONS = {
    "monitor final candle close",
    "review evidence",
    "inspect invalidation context",
    "evaluate outcome after horizon",
    "run news correlation",
    "request human review",
    "wait for more final candles",
}
BLOCKED_OUTPUT_TERMS = (
    "buy",
    "sell",
    "enter",
    "exit",
    "stop loss",
    "take profit",
    "long now",
    "short now",
    "leverage",
    "place order",
)


@dataclass(frozen=True)
class SetupContextArtifacts:
    signal: Signal
    analysis_run: AnalysisRun
    confidence_components: list[SignalConfidenceComponent]
    evidence: list[SignalEvidence]
    risk_notes: list[SignalRiskNote]
    selected_pattern_candidate: PatternCandidate | None
    recent_final_candles: list[Candle]
    feature_snapshot: FeatureSnapshot | None
    advanced_feature_snapshot: AdvancedFeatureSnapshot | None
    market_regime: MarketRegimeContext | None
    market_session: MarketSessionContext | None
    multi_timeframe_context: MultiTimeframeContext | None
    cross_asset_context_run: CrossAssetContextRun | None
    cross_asset_results: list[CrossAssetContextResult]
    outcomes: list[SignalOutcome]
    data_quality_run: DataQualityRun | None
    decision_readiness: DecisionReadinessAssessment | None


@dataclass(frozen=True)
class QualityScoreResult:
    score: Decimal
    components: dict[str, dict[str, object]]


class SetupContextBuilder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build(self, artifacts: SetupContextArtifacts) -> SetupContext:
        signal = artifacts.signal
        directional_bias = derive_directional_bias(signal)
        support_resistance = (
            artifacts.advanced_feature_snapshot.support_resistance_json
            if artifacts.advanced_feature_snapshot is not None
            else None
        )
        observation_zones = build_observation_zones(
            support_resistance=support_resistance,
            recent_candles=artifacts.recent_final_candles,
        )
        target_context_zones = build_target_context_zones(
            directional_bias=directional_bias.value,
            observation_zones=observation_zones,
            recent_candles=artifacts.recent_final_candles,
        )
        invalidation_context = build_invalidation_context(
            directional_bias=directional_bias.value,
            observation_zones=observation_zones,
            recent_candles=artifacts.recent_final_candles,
        )
        timeframe_agreement = build_timeframe_agreement(artifacts.multi_timeframe_context)
        risk_notes = build_risk_notes(artifacts.risk_notes, artifacts.selected_pattern_candidate)
        data_quality_warnings = build_data_quality_warnings(artifacts)
        avoid_reasons = build_avoid_reasons(
            artifacts=artifacts,
            directional_bias=directional_bias.value,
            data_quality_warnings=data_quality_warnings,
        )
        wait_conditions = build_wait_conditions(
            artifacts=artifacts,
            avoid_reasons=avoid_reasons,
            timeframe_agreement=timeframe_agreement,
        )
        next_observations = build_next_observations(
            artifacts=artifacts,
            avoid_reasons=avoid_reasons,
            timeframe_agreement=timeframe_agreement,
        )
        quality = calculate_setup_quality(
            artifacts=artifacts,
            directional_bias=directional_bias.value,
            timeframe_agreement=timeframe_agreement,
        )
        setup_quality_label = quality_label(
            score=quality.score,
            status=signal.classification_status,
            avoid_reasons=avoid_reasons,
            settings=self.settings,
        )
        status = setup_status(
            signal=signal,
            quality_label=setup_quality_label,
            warnings=data_quality_warnings + avoid_reasons + wait_conditions,
        )
        summary = build_summary(
            directional_bias=directional_bias.value,
            quality_label=setup_quality_label.value,
            status=status.value,
            avoid_count=len(avoid_reasons),
            wait_count=len(wait_conditions),
        )
        metadata = build_metadata(artifacts, quality)
        setup_context = SetupContext(
            workspace_id=signal.workspace_id,
            signal_id=signal.id,
            analysis_run_id=signal.analysis_run_id,
            symbol_id=signal.symbol_id,
            timeframe=signal.timeframe,
            context_version=self.settings.setup_context_version,
            status=status.value,
            directional_bias=directional_bias.value,
            setup_quality_label=setup_quality_label.value,
            setup_quality_score=quality.score,
            invalidation_context_json=to_json_value(invalidation_context),
            observation_zones_json=to_json_value(observation_zones),
            target_context_zones_json=to_json_value(target_context_zones),
            wait_conditions_json=to_json_value(wait_conditions),
            avoid_reasons_json=to_json_value(avoid_reasons),
            timeframe_agreement_json=to_json_value(timeframe_agreement),
            data_quality_warnings_json=to_json_value(data_quality_warnings),
            risk_notes_json=to_json_value(risk_notes),
            next_observations_json=to_json_value(next_observations),
            summary=summary,
            metadata_json=to_json_value(metadata),
        )
        assert_setup_context_safety(setup_context)
        return setup_context


def derive_directional_bias(signal: Signal) -> SetupContextDirectionalBias:
    if signal.classification_status != SignalClassificationStatus.SIGNAL.value:
        if signal.bias == SetupContextDirectionalBias.NEUTRAL.value:
            return SetupContextDirectionalBias.NEUTRAL
        return SetupContextDirectionalBias.UNCLEAR
    if signal.bias == SetupContextDirectionalBias.BULLISH.value:
        return SetupContextDirectionalBias.BULLISH
    if signal.bias == SetupContextDirectionalBias.BEARISH.value:
        return SetupContextDirectionalBias.BEARISH
    if signal.bias == SetupContextDirectionalBias.NEUTRAL.value:
        return SetupContextDirectionalBias.NEUTRAL
    return SetupContextDirectionalBias.UNCLEAR


def calculate_setup_quality(
    artifacts: SetupContextArtifacts,
    directional_bias: str,
    timeframe_agreement: dict[str, object],
) -> QualityScoreResult:
    component_scores = {
        "confidence": confidence_score(artifacts.signal),
        "evidence_alignment": evidence_alignment_score(artifacts.evidence, directional_bias),
        "risk_notes": risk_note_score(artifacts.risk_notes),
        "market_regime": market_regime_score(artifacts.market_regime, directional_bias),
        "multi_timeframe": multi_timeframe_score(timeframe_agreement),
        "data_quality": data_quality_score(
            artifacts.data_quality_run,
            artifacts.recent_final_candles,
        ),
        "outcome_context": outcome_context_score(artifacts.outcomes),
        "readiness_context": readiness_context_score(artifacts.decision_readiness),
    }
    weighted = sum(
        component_scores[name] * QUALITY_COMPONENT_WEIGHTS[name]
        for name in QUALITY_COMPONENT_WEIGHTS
    )
    return QualityScoreResult(
        score=decimal_score(weighted),
        components={
            name: {
                "score": decimal_string(score),
                "weight": decimal_string(QUALITY_COMPONENT_WEIGHTS[name]),
            }
            for name, score in component_scores.items()
        },
    )


def confidence_score(signal: Signal) -> Decimal:
    return clamp(Decimal(signal.confidence_score))


def evidence_alignment_score(evidence: list[SignalEvidence], directional_bias: str) -> Decimal:
    if directional_bias not in {"bullish", "bearish"}:
        return Decimal("0.5000")
    support_weight = ZERO
    conflict_weight = ZERO
    opposite = "bearish" if directional_bias == "bullish" else "bullish"
    for item in evidence:
        direction = item.direction.lower()
        weight = clamp(Decimal(item.weight))
        if directional_bias in direction:
            support_weight += weight
        elif opposite in direction:
            conflict_weight += weight
    if support_weight == ZERO and conflict_weight == ZERO:
        return Decimal("0.5000")
    return clamp(support_weight / (support_weight + conflict_weight))


def risk_note_score(risk_notes: list[SignalRiskNote]) -> Decimal:
    penalty = sum((RISK_PENALTIES.get(note.severity, Decimal("0.15")) for note in risk_notes), ZERO)
    return clamp(ONE - min(Decimal("0.90"), penalty))


def market_regime_score(
    market_regime: MarketRegimeContext | None,
    directional_bias: str,
) -> Decimal:
    if market_regime is None:
        return Decimal("0.5500")
    trend = market_regime.trend_regime
    range_regime = market_regime.range_regime
    if directional_bias == "bullish":
        if trend == "uptrend" or range_regime in {"breakout", "range_retest"}:
            return Decimal("0.8500")
        if trend == "downtrend" or range_regime == "breakdown":
            return Decimal("0.3000")
    if directional_bias == "bearish":
        if trend == "downtrend" or range_regime in {"breakdown", "range_retest"}:
            return Decimal("0.8500")
        if trend == "uptrend" or range_regime == "breakout":
            return Decimal("0.3000")
    if range_regime in {"fakeout_risk", "inside_range"} or trend in {"sideways", "mixed"}:
        return Decimal("0.4500")
    return Decimal("0.6000")


def multi_timeframe_score(timeframe_agreement: dict[str, object]) -> Decimal:
    score = timeframe_agreement.get("agreementScore")
    if score is not None:
        return clamp(Decimal(str(score)))
    label = str(timeframe_agreement.get("agreement") or "unknown")
    return {
        "aligned": Decimal("0.8500"),
        "mixed": Decimal("0.5500"),
        "conflicting": Decimal("0.2500"),
        "unknown": Decimal("0.4500"),
    }.get(label, Decimal("0.4500"))


def data_quality_score(
    data_quality_run: DataQualityRun | None,
    recent_final_candles: list[Candle],
) -> Decimal:
    if data_quality_run is not None:
        return clamp(Decimal(data_quality_run.quality_score))
    if recent_final_candles:
        quality_values = [
            Decimal(candle.quality_score)
            for candle in recent_final_candles
            if candle.quality_score is not None
        ]
        if quality_values:
            return clamp(sum(quality_values, ZERO) / Decimal(len(quality_values)))
        return Decimal("0.6500")
    return Decimal("0.2500")


def outcome_context_score(outcomes: list[SignalOutcome]) -> Decimal:
    if not outcomes:
        return Decimal("0.5500")
    labels = {outcome.outcome_label for outcome in outcomes}
    if labels & {"continuation", "partial_follow_through"}:
        return Decimal("0.7000")
    if labels & {"reversal", "no_follow_through"}:
        return Decimal("0.3500")
    if labels & {"insufficient_data", "failed"}:
        return Decimal("0.4000")
    return Decimal("0.5500")


def readiness_context_score(readiness: DecisionReadinessAssessment | None) -> Decimal:
    if readiness is None:
        return Decimal("0.5500")
    return {
        "ready": Decimal("0.8500"),
        "review_recommended": Decimal("0.6000"),
        "blocked": Decimal("0.2500"),
        "insufficient_context": Decimal("0.4000"),
    }.get(readiness.readiness_label, Decimal("0.5000"))


def quality_label(
    score: Decimal,
    status: str,
    avoid_reasons: list[dict[str, object]],
    settings: Settings,
) -> SetupQualityLabel:
    if status in {
        SignalClassificationStatus.NO_SIGNAL.value,
        SignalClassificationStatus.UNCLEAR.value,
        SignalClassificationStatus.INSUFFICIENT_EVIDENCE.value,
    }:
        return SetupQualityLabel.INSUFFICIENT_CONTEXT
    if any(reason.get("severity") == "critical" for reason in avoid_reasons):
        return SetupQualityLabel.AVOID_CONDITION
    if any(reason.get("severity") == "high" for reason in avoid_reasons):
        return SetupQualityLabel.REVIEW_REQUIRED
    if score >= settings.setup_context_strong_threshold:
        return SetupQualityLabel.STRONG_CONTEXT
    if score >= settings.setup_context_acceptable_threshold:
        return SetupQualityLabel.ACCEPTABLE_CONTEXT
    if score >= settings.setup_context_review_threshold:
        return SetupQualityLabel.MIXED_CONTEXT
    return SetupQualityLabel.REVIEW_REQUIRED


def setup_status(
    signal: Signal,
    quality_label: SetupQualityLabel,
    warnings: list[dict[str, object]],
) -> SetupContextStatus:
    if signal.classification_status in {
        SignalClassificationStatus.NO_SIGNAL.value,
        SignalClassificationStatus.UNCLEAR.value,
        SignalClassificationStatus.INSUFFICIENT_EVIDENCE.value,
    }:
        return SetupContextStatus.INSUFFICIENT_CONTEXT
    if quality_label in {SetupQualityLabel.AVOID_CONDITION, SetupQualityLabel.REVIEW_REQUIRED}:
        return SetupContextStatus.COMPLETED_WITH_WARNINGS
    if warnings:
        return SetupContextStatus.COMPLETED_WITH_WARNINGS
    return SetupContextStatus.COMPLETED


def build_timeframe_agreement(
    context: MultiTimeframeContext | None,
) -> dict[str, object]:
    if context is None:
        return {
            "agreement": "unknown",
            "agreementScore": None,
            "source": "multi_timeframe_context_missing",
            "details": {
                "trendAlignment": "unknown",
                "volatilityAlignment": "unknown",
                "rangeAlignment": "unknown",
            },
        }
    agreement = {
        "strong": "aligned",
        "acceptable": "aligned",
        "mixed": "mixed",
        "conflicting": "conflicting",
        "insufficient_context": "unknown",
    }.get(context.agreement_label, "unknown")
    return {
        "agreement": agreement,
        "agreementLabel": context.agreement_label,
        "agreementScore": decimal_string(Decimal(context.agreement_score)),
        "source": "multi_timeframe_context",
        "contextTimeframes": context.context_timeframes_json,
        "details": {
            "trendAlignment": context.trend_alignment,
            "volatilityAlignment": context.volatility_alignment,
            "rangeAlignment": context.range_alignment,
        },
    }


def build_risk_notes(
    risk_notes: list[SignalRiskNote],
    selected_pattern_candidate: PatternCandidate | None,
) -> list[dict[str, object]]:
    notes = [
        {
            "code": note.code,
            "severity": note.severity,
            "message": safe_text(note.message),
            "source": "signal_risk_note",
            "metadata": note.metadata_json,
        }
        for note in risk_notes
    ]
    if selected_pattern_candidate is not None:
        for note in selected_pattern_candidate.risk_notes_json[:10]:
            if isinstance(note, dict):
                notes.append(
                    {
                        "code": str(note.get("code") or "pattern_candidate_risk"),
                        "severity": str(note.get("severity") or "low"),
                        "message": safe_text(
                            str(note.get("message") or "Pattern candidate risk context")
                        ),
                        "source": "selected_pattern_candidate",
                        "metadata": note,
                    }
                )
    return notes[:20]


def build_data_quality_warnings(
    artifacts: SetupContextArtifacts,
) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    if not artifacts.recent_final_candles:
        warnings.append(
            {
                "code": "insufficient_candles",
                "severity": "high",
                "message": "Insufficient final candles for setup context",
            }
        )
    if artifacts.data_quality_run is None:
        warnings.append(
            {
                "code": "data_quality_context_missing",
                "severity": "low",
                "message": "Data quality context is missing",
            }
        )
    elif artifacts.data_quality_run.quality_label in {"degraded", "poor", "insufficient_data"}:
        severity = "medium" if artifacts.data_quality_run.quality_label == "degraded" else "high"
        warnings.append(
            {
                "code": f"data_quality_{artifacts.data_quality_run.quality_label}",
                "severity": severity,
                "message": f"Data quality label is {artifacts.data_quality_run.quality_label}",
                "metadata": {
                    "qualityScore": decimal_string(
                        Decimal(artifacts.data_quality_run.quality_score)
                    ),
                    "findingCount": artifacts.data_quality_run.finding_count,
                },
            }
        )
    if artifacts.analysis_run.status != "completed":
        warnings.append(
            {
                "code": "analysis_run_not_completed",
                "severity": "high",
                "message": "Analysis run is not completed",
            }
        )
    if artifacts.recent_final_candles:
        latest_candle = artifacts.recent_final_candles[-1]
        if latest_candle.timestamp < artifacts.analysis_run.end_time:
            warnings.append(
                {
                    "code": "data_stale",
                    "severity": "medium",
                    "message": "Latest final candle is older than the analysis window end",
                    "metadata": {
                        "latestFinalCandleTime": latest_candle.timestamp.isoformat(),
                        "analysisEndTime": artifacts.analysis_run.end_time.isoformat(),
                    },
                }
            )
    return warnings


def build_avoid_reasons(
    artifacts: SetupContextArtifacts,
    directional_bias: str,
    data_quality_warnings: list[dict[str, object]],
) -> list[dict[str, object]]:
    reasons: list[dict[str, object]] = []
    for warning in data_quality_warnings:
        if warning.get("severity") in {"medium", "high", "critical"}:
            reasons.append(
                {
                    "code": warning.get("code"),
                    "severity": warning.get("severity"),
                    "message": warning.get("message"),
                    "source": "data_quality",
                }
            )
    if directional_bias == "unclear":
        reasons.append(
            {
                "code": "insufficient_context",
                "severity": "high",
                "message": "Directional setup context is unclear",
                "source": "signal",
            }
        )
    if has_evidence_conflict(artifacts.evidence, directional_bias):
        reasons.append(
            {
                "code": "evidence_conflict",
                "severity": "medium",
                "message": "Evidence conflict requires review",
                "source": "signal_evidence",
            }
        )
    if (
        artifacts.market_regime is not None
        and artifacts.market_regime.range_regime == "fakeout_risk"
    ):
        reasons.append(
            {
                "code": "fakeout_risk",
                "severity": "medium",
                "message": "Fakeout risk is present in market regime context",
                "source": "market_regime",
            }
        )
    if (
        artifacts.market_regime is not None
        and artifacts.market_regime.range_regime == "inside_range"
    ):
        reasons.append(
            {
                "code": "chop_range_conditions",
                "severity": "medium",
                "message": "Range conditions require review",
                "source": "market_regime",
            }
        )
    if (
        artifacts.decision_readiness is not None
        and artifacts.decision_readiness.readiness_label == "blocked"
    ):
        reasons.append(
            {
                "code": "unresolved_critical_review",
                "severity": "critical",
                "message": "Decision readiness context is blocked",
                "source": "decision_readiness",
            }
        )
    for note in artifacts.risk_notes:
        if note.severity in {"high", "critical"}:
            reasons.append(
                {
                    "code": note.code,
                    "severity": note.severity,
                    "message": safe_text(note.message),
                    "source": "signal_risk_note",
                }
            )
    return dedupe_dicts(reasons)[:20]


def build_wait_conditions(
    artifacts: SetupContextArtifacts,
    avoid_reasons: list[dict[str, object]],
    timeframe_agreement: dict[str, object],
) -> list[dict[str, object]]:
    conditions = [
        {
            "code": "monitor_final_candle_close",
            "message": "Monitor final candle close",
            "source": "setup_context_policy",
        }
    ]
    if any(reason.get("code") in {"data_stale", "data_quality_poor"} for reason in avoid_reasons):
        conditions.append(
            {
                "code": "wait_for_data_freshness",
                "message": "Wait for data freshness",
                "source": "data_quality",
            }
        )
    if not artifacts.outcomes:
        conditions.append(
            {
                "code": "wait_for_outcome_evaluation",
                "message": "Wait for outcome evaluation",
                "source": "outcomes",
            }
        )
    if (
        artifacts.multi_timeframe_context is None
        or timeframe_agreement.get("agreement") != "aligned"
    ):
        conditions.append(
            {
                "code": "wait_for_multi_timeframe_agreement",
                "message": "Wait for multi-timeframe agreement",
                "source": "multi_timeframe_context",
            }
        )
    if (
        artifacts.decision_readiness is None
        or artifacts.decision_readiness.readiness_label != "ready"
    ):
        conditions.append(
            {
                "code": "wait_for_human_review",
                "message": "Wait for human review",
                "source": "decision_readiness",
            }
        )
    conditions.append(
        {
            "code": "wait_for_news_correlation",
            "message": "Wait for news correlation",
            "source": "news_context",
        }
    )
    return dedupe_dicts(conditions)


def build_next_observations(
    artifacts: SetupContextArtifacts,
    avoid_reasons: list[dict[str, object]],
    timeframe_agreement: dict[str, object],
) -> list[dict[str, object]]:
    observations = [
        "monitor final candle close",
        "review evidence",
        "inspect invalidation context",
    ]
    if not artifacts.outcomes:
        observations.append("evaluate outcome after horizon")
    observations.append("run news correlation")
    if avoid_reasons or timeframe_agreement.get("agreement") in {"mixed", "conflicting", "unknown"}:
        observations.append("request human review")
    if not artifacts.recent_final_candles or len(artifacts.recent_final_candles) < 3:
        observations.append("wait for more final candles")
    return [
        {"observation": observation, "source": "setup_context_policy"}
        for observation in observations
        if observation in ALLOWED_NEXT_OBSERVATIONS
    ]


def build_metadata(
    artifacts: SetupContextArtifacts,
    quality: QualityScoreResult,
) -> dict[str, object]:
    return {
        "qualityComponents": quality.components,
        "artifactAvailability": {
            "confidenceComponents": len(artifacts.confidence_components),
            "evidence": len(artifacts.evidence),
            "riskNotes": len(artifacts.risk_notes),
            "selectedPatternCandidate": artifacts.selected_pattern_candidate is not None,
            "recentFinalCandles": len(artifacts.recent_final_candles),
            "featureSnapshot": artifacts.feature_snapshot is not None,
            "advancedFeatureSnapshot": artifacts.advanced_feature_snapshot is not None,
            "marketRegime": artifacts.market_regime is not None,
            "marketSession": artifacts.market_session is not None,
            "multiTimeframeContext": artifacts.multi_timeframe_context is not None,
            "crossAssetContext": artifacts.cross_asset_context_run is not None,
            "crossAssetResults": len(artifacts.cross_asset_results),
            "outcomes": len(artifacts.outcomes),
            "dataQualityRun": artifacts.data_quality_run is not None,
            "decisionReadiness": artifacts.decision_readiness is not None,
        },
        "marketContext": {
            "marketRegime": compact_market_regime(artifacts.market_regime),
            "marketSession": compact_market_session(artifacts.market_session),
            "crossAsset": compact_cross_asset(
                artifacts.cross_asset_context_run,
                artifacts.cross_asset_results,
            ),
            "outcomes": [compact_outcome(outcome) for outcome in artifacts.outcomes[:5]],
        },
        "policy": {
            "backendOnly": True,
            "nonAdvisory": True,
            "notATradeInstruction": True,
            "noBrokerExecution": True,
            "noSignalMutation": True,
            "noStrategyProfileMutation": True,
            "noAlerts": True,
            "noLlmClassification": True,
        },
    }


def compact_market_regime(market_regime: MarketRegimeContext | None) -> dict[str, object] | None:
    if market_regime is None:
        return None
    return {
        "trendRegime": market_regime.trend_regime,
        "volatilityRegime": market_regime.volatility_regime,
        "rangeRegime": market_regime.range_regime,
        "dataQualityLabel": market_regime.data_quality_label,
        "confidenceScore": decimal_string(Decimal(market_regime.confidence_score)),
    }


def compact_market_session(market_session: MarketSessionContext | None) -> dict[str, object] | None:
    if market_session is None:
        return None
    return {
        "sessionLabel": market_session.session_label,
        "timezoneName": market_session.timezone_name,
        "confidenceScore": decimal_string(Decimal(market_session.confidence_score)),
    }


def compact_cross_asset(
    context_run: CrossAssetContextRun | None,
    results: list[CrossAssetContextResult],
) -> dict[str, object] | None:
    if context_run is None:
        return None
    return {
        "status": context_run.status,
        "resultCount": context_run.result_count,
        "results": [
            {
                "comparedSymbolId": str(result.compared_symbol_id),
                "alignmentLabel": result.alignment_label,
                "leadLagLabel": result.lead_lag_label,
                "divergenceScore": decimal_string(Decimal(result.divergence_score)),
                "dataQualityLabel": result.data_quality_label,
            }
            for result in results[:5]
        ],
    }


def compact_outcome(outcome: SignalOutcome) -> dict[str, object]:
    return {
        "horizonMinutes": outcome.horizon_minutes,
        "evaluationStatus": outcome.evaluation_status,
        "outcomeLabel": outcome.outcome_label,
        "directionFollowed": outcome.direction_followed,
        "reversalDetected": outcome.reversal_detected,
        "movementQuality": outcome.movement_quality,
    }


def build_summary(
    directional_bias: str,
    quality_label: str,
    status: str,
    avoid_count: int,
    wait_count: int,
) -> str:
    return (
        f"Setup context is {status} with {directional_bias} bias and "
        f"{quality_label}. Review {avoid_count} avoid reason(s) and "
        f"{wait_count} wait condition(s). Not a trade instruction."
    )


def has_evidence_conflict(evidence: list[SignalEvidence], directional_bias: str) -> bool:
    if directional_bias not in {"bullish", "bearish"}:
        return bool(evidence)
    opposite = "bearish" if directional_bias == "bullish" else "bullish"
    support = any(directional_bias in item.direction.lower() for item in evidence)
    conflict = any(opposite in item.direction.lower() for item in evidence)
    return support and conflict


def dedupe_dicts(items: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[tuple[object, object]] = set()
    deduped: list[dict[str, object]] = []
    for item in items:
        key = (item.get("code"), item.get("message"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def safe_text(value: str) -> str:
    output = value
    replacements = {
        "stop loss": "invalidation context",
        "take profit": "target context",
        "entry": "observation",
        "enter": "observe",
        "exit": "close review",
        "buy": "bullish context",
        "sell": "bearish context",
        "leverage": "risk exposure",
        "place order": "request review",
    }
    for blocked, replacement in replacements.items():
        output = output.replace(blocked, replacement)
        output = output.replace(blocked.title(), replacement)
    return output


def assert_setup_context_safety(setup_context: SetupContext) -> None:
    payload = to_json_value(setup_context_payload(setup_context))
    text = " ".join(str(value).lower() for value in flatten_values(payload))
    blocked = [
        term for term in BLOCKED_OUTPUT_TERMS if term in text and term not in {"enter", "exit"}
    ]
    blocked.extend(term for term in ("enter", "exit") if f" {term} " in f" {text} ")
    if blocked:
        msg = f"Setup context output contains blocked language: {sorted(set(blocked))}"
        raise ValueError(msg)
    observations = {
        str(item.get("observation"))
        for item in setup_context.next_observations_json
        if isinstance(item, dict)
    }
    if not observations.issubset(ALLOWED_NEXT_OBSERVATIONS):
        msg = "Setup context output contains unsupported next observations"
        raise ValueError(msg)


def setup_context_payload(setup_context: SetupContext) -> dict[str, object]:
    return {
        "invalidation": setup_context.invalidation_context_json,
        "observationZones": setup_context.observation_zones_json,
        "targetContextZones": setup_context.target_context_zones_json,
        "waitConditions": setup_context.wait_conditions_json,
        "avoidReasons": setup_context.avoid_reasons_json,
        "timeframeAgreement": setup_context.timeframe_agreement_json,
        "dataQualityWarnings": setup_context.data_quality_warnings_json,
        "riskNotes": setup_context.risk_notes_json,
        "nextObservations": setup_context.next_observations_json,
        "summary": setup_context.summary,
        "metadata": setup_context.metadata_json,
    }


def flatten_values(value: object) -> list[object]:
    if isinstance(value, dict):
        values: list[object] = []
        for key, item in value.items():
            values.append(key)
            values.extend(flatten_values(item))
        return values
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(flatten_values(item))
        return values
    return [value]


def to_json_value(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [to_json_value(item) for item in value]
    if isinstance(value, Decimal):
        return decimal_string(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def clamp(value: Decimal) -> Decimal:
    return min(ONE, max(ZERO, value))


def decimal_score(value: Decimal) -> Decimal:
    return clamp(value).quantize(FOUR_PLACES)


def decimal_string(value: Decimal) -> str:
    return str(decimal_score(value))
