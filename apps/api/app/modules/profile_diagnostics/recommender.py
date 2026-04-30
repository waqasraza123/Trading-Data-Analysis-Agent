from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.modules.profile_diagnostics.calculator import (
    DiagnosticThresholds,
    PatternOutcomeDiagnosticResult,
    StrategyProfileDiagnosticResult,
)
from app.modules.profile_diagnostics.models import (
    CalibrationRecommendationSeverity,
    CalibrationRecommendationStatus,
    CalibrationRecommendationType,
    DiagnosticLabel,
)
from app.modules.strategy_profiles.models import StrategyProfile


@dataclass(frozen=True)
class CalibrationRecommendationDraft:
    recommendation_type: CalibrationRecommendationType
    strategy_profile_key: str | None
    strategy_profile_version: str | None
    pattern_type: str | None
    symbol_id: UUID | None
    timeframe: str | None
    horizon_minutes: int | None
    severity: CalibrationRecommendationSeverity
    status: CalibrationRecommendationStatus
    title: str
    rationale: str
    suggested_change_json: dict[str, object] = field(default_factory=dict)
    evidence_json: dict[str, object] = field(default_factory=dict)


class ProfileCalibrationRecommender:
    def build_recommendations(
        self,
        profile_diagnostics: list[StrategyProfileDiagnosticResult],
        pattern_diagnostics: list[PatternOutcomeDiagnosticResult],
        profiles_by_key_version: dict[tuple[str, str | None], StrategyProfile],
        minimum_sample_size: int,
        thresholds: DiagnosticThresholds,
    ) -> list[CalibrationRecommendationDraft]:
        recommendations: list[CalibrationRecommendationDraft] = []
        for diagnostic in profile_diagnostics:
            recommendations.extend(
                self.profile_recommendations(
                    diagnostic=diagnostic,
                    profile=profiles_by_key_version.get(
                        (diagnostic.strategy_profile_key, diagnostic.strategy_profile_version)
                    ),
                    minimum_sample_size=minimum_sample_size,
                    thresholds=thresholds,
                )
            )
        for pattern_diagnostic in pattern_diagnostics:
            recommendations.extend(
                self.pattern_recommendations(
                    diagnostic=pattern_diagnostic,
                    thresholds=thresholds,
                )
            )
        return deduplicate_recommendations(recommendations)

    def profile_recommendations(
        self,
        diagnostic: StrategyProfileDiagnosticResult,
        profile: StrategyProfile | None,
        minimum_sample_size: int,
        thresholds: DiagnosticThresholds,
    ) -> list[CalibrationRecommendationDraft]:
        if diagnostic.sample_size < minimum_sample_size:
            return [
                CalibrationRecommendationDraft(
                    recommendation_type=CalibrationRecommendationType.INCREASE_SAMPLE_SIZE,
                    strategy_profile_key=diagnostic.strategy_profile_key,
                    strategy_profile_version=diagnostic.strategy_profile_version,
                    pattern_type=None,
                    symbol_id=diagnostic.symbol_id,
                    timeframe=diagnostic.timeframe,
                    horizon_minutes=diagnostic.horizon_minutes,
                    severity=CalibrationRecommendationSeverity.INFO,
                    status=CalibrationRecommendationStatus.OPEN,
                    title="Increase evaluated outcome sample",
                    rationale=(
                        "This diagnostic has too few evaluated outcomes for a stable "
                        "profile review."
                    ),
                    evidence_json=evidence_from_profile_diagnostic(diagnostic),
                )
            ]
        recommendations: list[CalibrationRecommendationDraft] = []
        if diagnostic.reversal_rate >= thresholds.high_reversal_rate:
            recommendations.append(
                CalibrationRecommendationDraft(
                    recommendation_type=CalibrationRecommendationType.REVIEW_MINIMUM_CONFIDENCE,
                    strategy_profile_key=diagnostic.strategy_profile_key,
                    strategy_profile_version=diagnostic.strategy_profile_version,
                    pattern_type=None,
                    symbol_id=diagnostic.symbol_id,
                    timeframe=diagnostic.timeframe,
                    horizon_minutes=diagnostic.horizon_minutes,
                    severity=severity_for_rate(diagnostic.reversal_rate),
                    status=CalibrationRecommendationStatus.OPEN,
                    title="Review minimum confidence",
                    rationale=(
                        "Observed reversal behavior is elevated for this filtered "
                        "profile sample."
                    ),
                    suggested_change_json=minimum_confidence_review(profile),
                    evidence_json=evidence_from_profile_diagnostic(diagnostic),
                )
            )
        if diagnostic.no_follow_through_rate >= thresholds.high_no_follow_through_rate:
            recommendations.append(
                CalibrationRecommendationDraft(
                    recommendation_type=CalibrationRecommendationType.REVIEW_CANDIDATE_STRENGTH,
                    strategy_profile_key=diagnostic.strategy_profile_key,
                    strategy_profile_version=diagnostic.strategy_profile_version,
                    pattern_type=None,
                    symbol_id=diagnostic.symbol_id,
                    timeframe=diagnostic.timeframe,
                    horizon_minutes=diagnostic.horizon_minutes,
                    severity=CalibrationRecommendationSeverity.MEDIUM,
                    status=CalibrationRecommendationStatus.OPEN,
                    title="Review candidate strength threshold",
                    rationale="Signals often do not show meaningful follow-through in this sample.",
                    suggested_change_json=candidate_strength_review(profile),
                    evidence_json=evidence_from_profile_diagnostic(diagnostic),
                )
            )
        if (
            diagnostic.confidence_alignment_score is not None
            and diagnostic.confidence_alignment_score
            <= thresholds.confidence_misalignment_threshold
        ):
            recommendations.append(
                CalibrationRecommendationDraft(
                    recommendation_type=CalibrationRecommendationType.REVIEW_MINIMUM_CONFIDENCE,
                    strategy_profile_key=diagnostic.strategy_profile_key,
                    strategy_profile_version=diagnostic.strategy_profile_version,
                    pattern_type=None,
                    symbol_id=diagnostic.symbol_id,
                    timeframe=diagnostic.timeframe,
                    horizon_minutes=diagnostic.horizon_minutes,
                    severity=CalibrationRecommendationSeverity.HIGH
                    if diagnostic.confidence_alignment_score < Decimal("0.30")
                    else CalibrationRecommendationSeverity.MEDIUM,
                    status=CalibrationRecommendationStatus.OPEN,
                    title="Review confidence calibration",
                    rationale=(
                        "Confidence scoring may be overestimating observed follow-through in "
                        "this sample."
                    ),
                    suggested_change_json=minimum_confidence_review(profile),
                    evidence_json=evidence_from_profile_diagnostic(diagnostic),
                )
            )
        if diagnostic.diagnostic_label == DiagnosticLabel.STRONG_FOLLOW_THROUGH:
            recommendations.append(
                CalibrationRecommendationDraft(
                    recommendation_type=CalibrationRecommendationType.NO_CHANGE,
                    strategy_profile_key=diagnostic.strategy_profile_key,
                    strategy_profile_version=diagnostic.strategy_profile_version,
                    pattern_type=None,
                    symbol_id=diagnostic.symbol_id,
                    timeframe=diagnostic.timeframe,
                    horizon_minutes=diagnostic.horizon_minutes,
                    severity=CalibrationRecommendationSeverity.INFO,
                    status=CalibrationRecommendationStatus.OPEN,
                    title="No profile change suggested",
                    rationale="Observed profile behavior appears stable for this filtered sample.",
                    evidence_json=evidence_from_profile_diagnostic(diagnostic),
                )
            )
        if (
            diagnostic.symbol_id is not None
            and diagnostic.timeframe is not None
            and (
                diagnostic.reversal_rate >= thresholds.high_reversal_rate
                or diagnostic.no_follow_through_rate >= thresholds.high_no_follow_through_rate
            )
        ):
            recommendations.append(
                CalibrationRecommendationDraft(
                    recommendation_type=CalibrationRecommendationType.MONITOR_SYMBOL_TIMEFRAME,
                    strategy_profile_key=diagnostic.strategy_profile_key,
                    strategy_profile_version=diagnostic.strategy_profile_version,
                    pattern_type=None,
                    symbol_id=diagnostic.symbol_id,
                    timeframe=diagnostic.timeframe,
                    horizon_minutes=diagnostic.horizon_minutes,
                    severity=CalibrationRecommendationSeverity.MEDIUM,
                    status=CalibrationRecommendationStatus.OPEN,
                    title="Monitor symbol and timeframe behavior",
                    rationale=(
                        "This symbol/timeframe/profile combination shows weaker "
                        "observed behavior."
                    ),
                    evidence_json=evidence_from_profile_diagnostic(diagnostic),
                )
            )
        return recommendations

    def pattern_recommendations(
        self,
        diagnostic: PatternOutcomeDiagnosticResult,
        thresholds: DiagnosticThresholds,
    ) -> list[CalibrationRecommendationDraft]:
        if diagnostic.sample_size == 0:
            return []
        if (
            diagnostic.reversal_rate < thresholds.high_reversal_rate
            and diagnostic.no_follow_through_rate < thresholds.high_no_follow_through_rate
        ):
            return []
        return [
            CalibrationRecommendationDraft(
                recommendation_type=CalibrationRecommendationType.REVIEW_PATTERN_DETECTOR,
                strategy_profile_key=diagnostic.strategy_profile_key,
                strategy_profile_version=None,
                pattern_type=diagnostic.pattern_type,
                symbol_id=diagnostic.symbol_id,
                timeframe=diagnostic.timeframe,
                horizon_minutes=diagnostic.horizon_minutes,
                severity=CalibrationRecommendationSeverity.MEDIUM,
                status=CalibrationRecommendationStatus.OPEN,
                title="Review pattern detector behavior",
                rationale=(
                    "This pattern shows elevated reversal or no-follow-through behavior across "
                    "the filtered sample."
                ),
                evidence_json=evidence_from_pattern_diagnostic(diagnostic),
            )
        ]


def minimum_confidence_review(profile: StrategyProfile | None) -> dict[str, object]:
    current_value = str(profile.minimum_confidence) if profile is not None else None
    return {
        "review": "minimum_confidence",
        "direction": "increase",
        "currentValue": current_value,
        "suggestedReviewRange": suggested_range(current_value),
    }


def candidate_strength_review(profile: StrategyProfile | None) -> dict[str, object]:
    current_value = str(profile.minimum_candidate_strength) if profile is not None else None
    return {
        "review": "minimum_candidate_strength",
        "direction": "increase",
        "currentValue": current_value,
        "suggestedReviewRange": suggested_range(current_value),
    }


def suggested_range(current_value: str | None) -> list[str]:
    if current_value is None:
        return []
    current = Decimal(current_value)
    lower = min(current + Decimal("0.0250"), Decimal("1.0000"))
    upper = min(current + Decimal("0.1000"), Decimal("1.0000"))
    return [str(lower), str(upper)]


def severity_for_rate(value: Decimal) -> CalibrationRecommendationSeverity:
    if value >= Decimal("0.50"):
        return CalibrationRecommendationSeverity.HIGH
    return CalibrationRecommendationSeverity.MEDIUM


def evidence_from_profile_diagnostic(
    diagnostic: StrategyProfileDiagnosticResult,
) -> dict[str, object]:
    return {
        "sampleSize": diagnostic.sample_size,
        "evaluatedCount": diagnostic.evaluated_count,
        "continuationRate": str(diagnostic.continuation_rate),
        "reversalRate": str(diagnostic.reversal_rate),
        "noFollowThroughRate": str(diagnostic.no_follow_through_rate),
        "confidenceAlignmentScore": (
            str(diagnostic.confidence_alignment_score)
            if diagnostic.confidence_alignment_score is not None
            else None
        ),
        "diagnosticLabel": diagnostic.diagnostic_label.value,
    }


def evidence_from_pattern_diagnostic(
    diagnostic: PatternOutcomeDiagnosticResult,
) -> dict[str, object]:
    return {
        "sampleSize": diagnostic.sample_size,
        "evaluatedCount": diagnostic.evaluated_count,
        "continuationRate": str(diagnostic.continuation_rate),
        "reversalRate": str(diagnostic.reversal_rate),
        "noFollowThroughRate": str(diagnostic.no_follow_through_rate),
        "diagnosticLabel": diagnostic.diagnostic_label.value,
    }


def deduplicate_recommendations(
    recommendations: list[CalibrationRecommendationDraft],
) -> list[CalibrationRecommendationDraft]:
    deduplicated: dict[tuple[object, ...], CalibrationRecommendationDraft] = {}
    for recommendation in recommendations:
        key = (
            recommendation.recommendation_type,
            recommendation.strategy_profile_key,
            recommendation.strategy_profile_version,
            recommendation.pattern_type,
            recommendation.symbol_id,
            recommendation.timeframe,
            recommendation.horizon_minutes,
        )
        deduplicated.setdefault(key, recommendation)
    return list(deduplicated.values())
