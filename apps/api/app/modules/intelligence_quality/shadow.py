from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.intelligence_quality.gates import FindingDraft, finding
from app.modules.intelligence_quality.models import (
    IntelligenceQualityFindingType,
    IntelligenceQualitySeverity,
    ShadowAgreement,
)
from app.modules.intelligence_quality.repository import IntelligenceQualityArtifacts
from app.modules.patterns.models import PatternCandidate
from app.modules.signals.conflicts import resolve_conflicts
from app.modules.signals.models import Signal
from app.modules.signals.service import SignalClassificationService, dominant_rejection_reason
from app.modules.strategy_profiles.models import StrategyProfile

SHADOW_CLASSIFICATION_VERSION = "shadow_profiles_v1"
SHADOW_CLASSIFICATION_DISABLED_VERSION = "shadow_not_requested_v1"


@dataclass(frozen=True)
class ShadowClassificationDraft:
    workspace_id: UUID
    analysis_run_id: UUID
    signal_id: UUID | None
    strategy_profile_key: str
    strategy_profile_version: str
    classification_status: str
    bias: str
    pattern_type: str | None
    confidence_score: Decimal | None
    confidence_label: str | None
    selected_candidate_id: UUID | None
    agreement_with_final: str
    disagreement_reason: str | None
    metadata_json: dict[str, object]


@dataclass(frozen=True)
class ShadowClassificationOutcome:
    results: list[ShadowClassificationDraft]
    findings: list[FindingDraft]


class ShadowClassificationService:
    def evaluate_profiles(
        self,
        artifacts: IntelligenceQualityArtifacts,
        profiles: list[StrategyProfile],
    ) -> ShadowClassificationOutcome:
        run = artifacts.analysis_run
        if run is None:
            return ShadowClassificationOutcome(results=[], findings=[])
        signal = artifacts.signal
        results = [
            self.evaluate_profile(
                workspace_id=run.workspace_id,
                analysis_run_id=run.id,
                signal=signal,
                candidates=artifacts.pattern_candidates,
                profile=profile,
                features=(
                    artifacts.feature_snapshot.features_json
                    if artifacts.feature_snapshot is not None
                    else None
                ),
                indicators=(
                    artifacts.indicator_snapshot.indicators_json
                    if artifacts.indicator_snapshot is not None
                    else None
                ),
            )
            for profile in profiles
        ]
        findings = self.findings_for_results(signal, results)
        return ShadowClassificationOutcome(results=results, findings=findings)

    def evaluate_profile(
        self,
        workspace_id: UUID,
        analysis_run_id: UUID,
        signal: Signal | None,
        candidates: list[PatternCandidate],
        profile: StrategyProfile,
        features: dict[str, object] | None,
        indicators: dict[str, object] | None,
    ) -> ShadowClassificationDraft:
        reason: str | None
        if not candidates:
            status = "no_signal"
            bias = "neutral"
            pattern_type = None
            confidence_score = None
            confidence_label = None
            selected_candidate_id = None
            reason = "no_pattern_candidates"
            agreement = ShadowAgreement.NO_CANDIDATE.value
        else:
            classifier = SignalClassificationService.__new__(SignalClassificationService)
            evaluations, rejections = classifier.evaluate_candidates(
                profiles=[profile],
                candidates=candidates,
                features=features,
                indicators=indicators,
            )
            if evaluations:
                decision = resolve_conflicts(evaluations)
                selected = decision.selected_evaluation
                status = decision.classification_status.value
                bias = decision.bias.value
                pattern_type = selected.candidate.pattern_type if selected is not None else None
                confidence_score = (
                    selected.confidence.confidence_score if selected is not None else None
                )
                confidence_label = (
                    selected.confidence.confidence_label.value if selected is not None else None
                )
                selected_candidate_id = selected.candidate.id if selected is not None else None
                reason = decision.no_signal_reason
                agreement = compare_with_final(
                    signal=signal,
                    classification_status=status,
                    bias=bias,
                    pattern_type=pattern_type,
                )
            else:
                reason = dominant_rejection_reason(rejections)
                status = (
                    "insufficient_evidence"
                    if reason in {"low_data_quality", "insufficient_evidence"}
                    else "no_signal"
                )
                bias = "neutral"
                pattern_type = None
                confidence_score = None
                confidence_label = None
                selected_candidate_id = None
                agreement = compare_with_final(
                    signal=signal,
                    classification_status=status,
                    bias=bias,
                    pattern_type=pattern_type,
                )
        return ShadowClassificationDraft(
            workspace_id=workspace_id,
            analysis_run_id=analysis_run_id,
            signal_id=signal.id if signal is not None else None,
            strategy_profile_key=profile.key,
            strategy_profile_version=profile.version,
            classification_status=status,
            bias=bias,
            pattern_type=pattern_type,
            confidence_score=confidence_score,
            confidence_label=confidence_label,
            selected_candidate_id=selected_candidate_id,
            agreement_with_final=agreement,
            disagreement_reason=reason if agreement != ShadowAgreement.AGREED.value else None,
            metadata_json={
                "diagnosticOnly": True,
                "profileName": profile.name,
                "candidateCount": len(candidates),
            },
        )

    def findings_for_results(
        self,
        signal: Signal | None,
        results: list[ShadowClassificationDraft],
    ) -> list[FindingDraft]:
        if not results:
            return []
        findings: list[FindingDraft] = []
        disagreements = [
            result
            for result in results
            if result.agreement_with_final
            not in {ShadowAgreement.AGREED.value, ShadowAgreement.NO_CANDIDATE.value}
        ]
        if disagreements:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.SHADOW_DISAGREEMENT,
                    IntelligenceQualitySeverity.MEDIUM,
                    "shadow_profiles_disagree",
                    "Shadow profiles disagree",
                    "One or more active profiles disagree with the persisted final signal.",
                    "signal",
                    signal.id if signal is not None else None,
                    metadata_json={"disagreementCount": len(disagreements)},
                )
            )
        agreed_count = sum(
            1 for result in results if result.agreement_with_final == ShadowAgreement.AGREED.value
        )
        agreement_ratio = Decimal(agreed_count) / Decimal(len(results))
        if agreement_ratio < Decimal("0.5000"):
            findings.append(
                finding(
                    IntelligenceQualityFindingType.SHADOW_DISAGREEMENT,
                    IntelligenceQualitySeverity.MEDIUM,
                    "low_profile_agreement",
                    "Low profile agreement",
                    "Less than half of active profiles agree with the persisted final signal.",
                    "signal",
                    signal.id if signal is not None else None,
                    metadata_json={
                        "agreementRatio": str(agreement_ratio.quantize(Decimal("0.0001")))
                    },
                )
            )
        elif agreement_ratio >= Decimal("0.8000"):
            findings.append(
                finding(
                    IntelligenceQualityFindingType.SHADOW_DISAGREEMENT,
                    IntelligenceQualitySeverity.INFO,
                    "high_profile_agreement",
                    "High profile agreement",
                    "Most active profiles agree with the persisted final signal.",
                    "signal",
                    signal.id if signal is not None else None,
                    metadata_json={
                        "agreementRatio": str(agreement_ratio.quantize(Decimal("0.0001")))
                    },
                )
            )
        if signal is not None and signal.classification_status == "signal":
            for result in results:
                if (
                    result.strategy_profile_key == "fakeout_protection"
                    and result.agreement_with_final == ShadowAgreement.DISAGREED_STATUS.value
                ):
                    findings.append(
                        finding(
                            IntelligenceQualityFindingType.SHADOW_DISAGREEMENT,
                            IntelligenceQualitySeverity.HIGH,
                            "fakeout_profile_disagrees_with_breakout",
                            "Fakeout profile disagreement",
                            "Fakeout protection profile blocks the persisted directional signal.",
                            "signal",
                            signal.id,
                        )
                    )
                if (
                    result.strategy_profile_key == "range_chop_avoidance"
                    and result.agreement_with_final == ShadowAgreement.DISAGREED_STATUS.value
                ):
                    findings.append(
                        finding(
                            IntelligenceQualityFindingType.SHADOW_DISAGREEMENT,
                            IntelligenceQualitySeverity.HIGH,
                            "range_chop_profile_blocks_directional_signal",
                            "Range/chop profile disagreement",
                            "Range/chop profile blocks the persisted directional signal.",
                            "signal",
                            signal.id,
                        )
                    )
        if disagreements:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.REVIEW_RECOMMENDATION,
                    IntelligenceQualitySeverity.MEDIUM,
                    "review_shadow_profile_disagreement",
                    "Review recommended for shadow disagreement",
                    "Review this signal because shadow profiles disagree on final classification.",
                    "signal",
                    signal.id if signal is not None else None,
                )
            )
        return findings


def compare_with_final(
    signal: Signal | None,
    classification_status: str,
    bias: str,
    pattern_type: str | None,
) -> str:
    if signal is None:
        return ShadowAgreement.NOT_APPLICABLE.value
    if signal.classification_status != classification_status:
        return ShadowAgreement.DISAGREED_STATUS.value
    if signal.bias != bias:
        return ShadowAgreement.DISAGREED_BIAS.value
    if signal.pattern_type != pattern_type:
        return ShadowAgreement.DISAGREED_PATTERN.value
    return ShadowAgreement.AGREED.value
