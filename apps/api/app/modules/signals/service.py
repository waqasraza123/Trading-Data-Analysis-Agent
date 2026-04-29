from collections.abc import Mapping
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun, AnalysisRunStatus
from app.modules.analysis.repository import AnalysisRepository
from app.modules.explanations.repository import DeterministicExplanationRepository
from app.modules.explanations.schemas import DeterministicExplanationRead
from app.modules.explanations.service import DeterministicExplanationService
from app.modules.features.repository import FeatureSnapshotRepository
from app.modules.indicators.repository import IndicatorSnapshotRepository
from app.modules.llm_explanations.repository import LlmExplanationRepository
from app.modules.llm_explanations.schemas import LlmExplanationRead
from app.modules.news.repository import NewsCorrelationRepository
from app.modules.news.schemas import NewsCorrelationRead
from app.modules.patterns.models import PatternCandidate
from app.modules.patterns.repository import PatternCandidateRepository
from app.modules.patterns.serialization import serialize_pattern_map
from app.modules.signals.confidence import (
    ConfidenceResult,
    calculate_confidence,
    clamp_score,
    decimal_feature,
    decimal_value,
    string_feature,
)
from app.modules.signals.conflicts import resolve_conflicts
from app.modules.signals.models import (
    Signal,
    SignalBias,
    SignalClassificationStatus,
    SignalConfidenceComponent,
    SignalConfidenceLabel,
    SignalEvidence,
    SignalRiskNote,
)
from app.modules.signals.repository import SignalRepository
from app.modules.signals.schemas import (
    SignalClassificationRead,
    SignalConfidenceComponentRead,
    SignalEvidenceRead,
    SignalRead,
    SignalRiskNoteRead,
)
from app.modules.signals.types import CandidateEvaluation, ConflictDecision, RejectedCandidate
from app.modules.strategy_profiles.models import StrategyProfile
from app.modules.strategy_profiles.repository import StrategyProfileRepository


class SignalClassificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.signal_repository = SignalRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.pattern_repository = PatternCandidateRepository(session)
        self.feature_repository = FeatureSnapshotRepository(session)
        self.indicator_repository = IndicatorSnapshotRepository(session)
        self.strategy_profile_repository = StrategyProfileRepository(session)
        self.explanation_repository = DeterministicExplanationRepository(session)
        self.llm_explanation_repository = LlmExplanationRepository(session)
        self.news_correlation_repository = NewsCorrelationRepository(session)
        self.explanation_service = DeterministicExplanationService(session)

    async def classify_analysis_run(self, analysis_run_id: UUID) -> SignalClassificationRead:
        run = await self.get_completed_run(analysis_run_id)
        try:
            signal = await self.classify_run(run, require_completed=True)
            await self.explanation_service.generate_for_signal(signal)
            await self.session.commit()
            return await self.get_signal_response(signal.id)
        except Exception:
            await self.session.rollback()
            raise

    async def classify_run(
        self,
        run: AnalysisRun,
        require_completed: bool,
        strategy_profiles: list[StrategyProfile] | None = None,
    ) -> Signal:
        if require_completed and run.status != AnalysisRunStatus.COMPLETED:
            raise AppError(
                422,
                "analysis_run_not_classifiable",
                "Only completed analysis runs can be classified manually",
            )
        await self.add_audit_log(
            run.id,
            "signal_classification_started",
            "Signal classification started",
        )
        await self.signal_repository.delete_for_analysis_run(run.id)
        candidates = await self.pattern_repository.list_by_analysis_run_id(run.id)
        feature_snapshot = await self.feature_repository.get_by_analysis_run_id(run.id)
        indicator_snapshot = await self.indicator_repository.get_by_analysis_run_id(run.id)
        profiles = (
            strategy_profiles
            if strategy_profiles is not None
            else await self.strategy_profile_repository.list_active_profiles()
        )
        await self.add_audit_log(
            run.id,
            "strategy_profiles_loaded",
            "Active strategy profiles loaded",
            {"profileCount": len(profiles)},
        )
        if not candidates:
            signal = await self.persist_no_candidate_signal(run)
            await self.add_audit_log(
                run.id,
                "no_signal_generated",
                "No signal generated because no pattern candidates exist",
                {"noSignalReason": "no_pattern_candidates"},
            )
            await self.add_audit_log(
                run.id,
                "signal_classification_completed",
                "Signal classification completed",
                {"signalId": str(signal.id)},
            )
            return signal
        if not profiles:
            signal = await self.persist_no_profile_signal(run, candidates)
            await self.add_audit_log(
                run.id,
                "no_signal_generated",
                "No signal generated because no active strategy profiles exist",
                {"noSignalReason": "no_profile_candidates"},
            )
            await self.add_audit_log(
                run.id,
                "signal_classification_completed",
                "Signal classification completed",
                {"signalId": str(signal.id)},
            )
            return signal
        evaluations, rejections = self.evaluate_candidates(
            profiles=profiles,
            candidates=candidates,
            features=feature_snapshot.features_json if feature_snapshot is not None else None,
            indicators=(
                indicator_snapshot.indicators_json
                if indicator_snapshot is not None
                else None
            ),
        )
        await self.add_audit_log(
            run.id,
            "pattern_candidates_ranked",
            "Pattern candidates evaluated against active profiles",
            {"eligibleCount": len(evaluations), "rejectedCount": len(rejections)},
        )
        if not evaluations:
            signal = await self.persist_no_eligible_signal(
                run=run,
                candidates=candidates,
                rejections=rejections,
                features=feature_snapshot.features_json if feature_snapshot is not None else None,
            )
            await self.add_audit_log(
                run.id,
                "no_signal_generated",
                "No signal generated because no candidates passed profile filters",
                {"noSignalReason": signal.no_signal_reason},
            )
            await self.add_audit_log(
                run.id,
                "signal_classification_completed",
                "Signal classification completed",
                {"signalId": str(signal.id)},
            )
            return signal
        decision = resolve_conflicts(evaluations)
        signal = await self.persist_decision(
            run=run,
            candidates=candidates,
            decision=decision,
            features=feature_snapshot.features_json if feature_snapshot is not None else None,
        )
        event_type = (
            "signal_selected"
            if signal.classification_status == SignalClassificationStatus.SIGNAL
            else "no_signal_generated"
        )
        await self.add_audit_log(
            run.id,
            event_type,
            "Signal classification output persisted",
            {
                "signalId": str(signal.id),
                "classificationStatus": signal.classification_status,
                "bias": signal.bias,
                "strategyProfileKey": signal.strategy_profile_key,
                "selectedPatternCandidateId": (
                    str(signal.selected_pattern_candidate_id)
                    if signal.selected_pattern_candidate_id is not None
                    else None
                ),
                "noSignalReason": signal.no_signal_reason,
            },
        )
        await self.add_audit_log(
            run.id,
            "signal_classification_completed",
            "Signal classification completed",
            {"signalId": str(signal.id)},
        )
        return signal

    async def get_by_analysis_run_id(self, analysis_run_id: UUID) -> SignalClassificationRead:
        run = await self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        signal = await self.signal_repository.get_by_analysis_run_id(analysis_run_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return await self.get_signal_response(signal.id)

    async def get_signal_response(self, signal_id: UUID) -> SignalClassificationRead:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        components = await self.signal_repository.list_confidence_components(signal.id)
        evidence = await self.signal_repository.list_evidence(signal.id)
        risk_notes = await self.signal_repository.list_risk_notes(signal.id)
        explanation = await self.explanation_repository.get_by_signal_id(signal.id)
        news_correlations = await self.news_correlation_repository.list_by_signal_id(signal.id)
        llm_explanation = await self.llm_explanation_repository.get_by_signal_id(signal.id)
        return SignalClassificationRead(
            analysis_run_id=signal.analysis_run_id,
            signal=SignalRead.model_validate(signal),
            confidence_components=[
                SignalConfidenceComponentRead.model_validate(component)
                for component in components
            ],
            evidence=[SignalEvidenceRead.model_validate(item) for item in evidence],
            risk_notes=[SignalRiskNoteRead.model_validate(note) for note in risk_notes],
            deterministic_explanation=(
                DeterministicExplanationRead.model_validate(explanation)
                if explanation is not None
                else None
            ),
            news_correlations=[
                NewsCorrelationRead.model_validate(correlation)
                for correlation in news_correlations
            ],
            llm_explanation=(
                LlmExplanationRead.model_validate(llm_explanation)
                if llm_explanation is not None
                else None
            ),
        )

    async def get_completed_run(self, analysis_run_id: UUID) -> AnalysisRun:
        run = await self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        if run.status != AnalysisRunStatus.COMPLETED:
            raise AppError(
                422,
                "analysis_run_not_classifiable",
                "Only completed analysis runs can be classified manually",
            )
        return run

    def evaluate_candidates(
        self,
        profiles: list[StrategyProfile],
        candidates: list[PatternCandidate],
        features: Mapping[str, Any] | None,
        indicators: Mapping[str, Any] | None,
    ) -> tuple[list[CandidateEvaluation], list[RejectedCandidate]]:
        evaluations: list[CandidateEvaluation] = []
        rejections: list[RejectedCandidate] = []
        for profile in profiles:
            for candidate in candidates:
                rejection = self.initial_rejection(profile, candidate)
                if rejection is not None:
                    rejections.append(rejection)
                    continue
                confidence = calculate_confidence(
                    candidate=candidate,
                    component_weights=profile.component_weights_json,
                    features=features,
                    indicators=indicators,
                )
                rejection = self.metric_rejection(profile, candidate, confidence, features)
                if rejection is not None:
                    rejections.append(rejection)
                    continue
                ranking_score = clamp_score(
                    (confidence.confidence_score * Decimal("0.70"))
                    + (candidate.strength_score * Decimal("0.30"))
                )
                evaluations.append(
                    CandidateEvaluation(
                        profile=profile,
                        candidate=candidate,
                        confidence=confidence,
                        ranking_score=ranking_score,
                        classifier_evidence=(
                            {
                                "evidence_type": "classification",
                                "direction": f"supports_{candidate.bias}",
                                "message": (
                                    f"{candidate.pattern_type} passed {profile.key} thresholds "
                                    f"with strength {candidate.strength_score} and confidence "
                                    f"{confidence.confidence_score}."
                                ),
                                "weight": "0.00000",
                                "metadata": {"strategyProfileKey": profile.key},
                            },
                        ),
                        risk_notes=confidence.risk_notes,
                    )
                )
        return evaluations, rejections

    def initial_rejection(
        self,
        profile: StrategyProfile,
        candidate: PatternCandidate,
    ) -> RejectedCandidate | None:
        allowed_patterns = set(profile.allowed_patterns_json)
        excluded_patterns = set(profile.excluded_patterns_json)
        if candidate.pattern_type in excluded_patterns:
            return rejected_candidate(
                profile,
                candidate,
                "unsupported_pattern_type",
                f"{candidate.pattern_type} is excluded by {profile.key}.",
            )
        if candidate.pattern_type not in allowed_patterns:
            return rejected_candidate(
                profile,
                candidate,
                "unsupported_pattern_type",
                f"{candidate.pattern_type} is not allowed by {profile.key}.",
            )
        if candidate.strength_score < profile.minimum_candidate_strength:
            return rejected_candidate(
                profile,
                candidate,
                "below_minimum_strength",
                (
                    f"{candidate.pattern_type} strength {candidate.strength_score} was below "
                    f"{profile.key} minimum {profile.minimum_candidate_strength}."
                ),
            )
        return None

    def metric_rejection(
        self,
        profile: StrategyProfile,
        candidate: PatternCandidate,
        confidence: ConfidenceResult,
        features: Mapping[str, Any] | None,
    ) -> RejectedCandidate | None:
        minimum_data_quality = decimal_value(profile.risk_filters_json.get("minimum_data_quality"))
        data_quality = decimal_feature(features, "dataQuality", "qualityScore")
        if (
            minimum_data_quality is not None
            and data_quality is not None
            and data_quality < minimum_data_quality
        ):
            return rejected_candidate(
                profile,
                candidate,
                "low_data_quality",
                (
                    f"Data quality {data_quality} was below {profile.key} minimum "
                    f"{minimum_data_quality}."
                ),
            )
        if confidence.confidence_score < profile.minimum_confidence:
            return rejected_candidate(
                profile,
                candidate,
                "below_minimum_confidence",
                (
                    f"{candidate.pattern_type} confidence {confidence.confidence_score} was below "
                    f"{profile.key} minimum {profile.minimum_confidence}."
                ),
            )
        if profile.risk_filters_json.get("compressed_volatility_blocks_directional") is True:
            volatility_state = string_feature(features, "volatility", "volatilityState")
            if candidate.bias in {"bullish", "bearish"} and volatility_state == "compressed":
                return rejected_candidate(
                    profile,
                    candidate,
                    "insufficient_evidence",
                    "Compressed volatility blocked directional classification.",
                )
        if profile.risk_filters_json.get("contradicting_trend_blocks_directional") is True:
            trend_state = string_feature(features, "trend", "trendState")
            if candidate.bias == "bullish" and trend_state == "short_term_downtrend":
                return rejected_candidate(
                    profile,
                    candidate,
                    "insufficient_evidence",
                    "Trend state strongly contradicted bullish classification.",
                )
            if candidate.bias == "bearish" and trend_state == "short_term_uptrend":
                return rejected_candidate(
                    profile,
                    candidate,
                    "insufficient_evidence",
                    "Trend state strongly contradicted bearish classification.",
                )
        return None

    async def persist_decision(
        self,
        run: AnalysisRun,
        candidates: list[PatternCandidate],
        decision: ConflictDecision,
        features: Mapping[str, Any] | None,
    ) -> Signal:
        selected = decision.selected_evaluation
        for candidate in candidates:
            candidate.is_selected = (
                selected is not None and candidate.id == selected.candidate.id
            )
        signal = self.build_signal(
            run=run,
            classification_status=decision.classification_status,
            bias=decision.bias,
            no_signal_reason=decision.no_signal_reason,
            summary=decision.summary,
            selected_evaluation=selected,
            features=features,
        )
        components = self.build_confidence_components(selected)
        evidence = self.build_evidence(selected, decision.evidence)
        risk_notes = self.build_risk_notes(selected, decision.risk_notes)
        return await self.signal_repository.create_signal(signal, components, evidence, risk_notes)

    async def persist_no_candidate_signal(self, run: AnalysisRun) -> Signal:
        signal = self.base_signal(
            run=run,
            classification_status=SignalClassificationStatus.NO_SIGNAL,
            bias=SignalBias.NEUTRAL,
            confidence_score=Decimal("0.0000"),
            confidence_label=SignalConfidenceLabel.LOW,
            summary="No signal generated because no pattern candidates were available.",
            no_signal_reason="no_pattern_candidates",
            features=None,
        )
        evidence = [
            SignalEvidence(
                evidence_type="classification",
                direction="neutral",
                message=(
                    "No signal generated because no persisted pattern candidates "
                    "were available."
                ),
                numeric_value=None,
                weight=Decimal("0.00000"),
                metadata_json={},
            )
        ]
        risk_notes = [
            SignalRiskNote(
                code="no_pattern_candidates",
                message="No persisted pattern candidates were available for classification.",
                severity="medium",
                metadata_json={},
            )
        ]
        return await self.signal_repository.create_signal(signal, [], evidence, risk_notes)

    async def persist_no_profile_signal(
        self,
        run: AnalysisRun,
        candidates: list[PatternCandidate],
    ) -> Signal:
        for candidate in candidates:
            candidate.is_selected = False
        signal = self.base_signal(
            run=run,
            classification_status=SignalClassificationStatus.INSUFFICIENT_EVIDENCE,
            bias=SignalBias.NEUTRAL,
            confidence_score=Decimal("0.0000"),
            confidence_label=SignalConfidenceLabel.LOW,
            summary="No signal generated because no active strategy profiles were available.",
            no_signal_reason="no_profile_candidates",
            features=None,
        )
        evidence = [
            SignalEvidence(
                evidence_type="classification",
                direction="neutral",
                message="No signal generated because no active strategy profiles were available.",
                numeric_value=None,
                weight=Decimal("0.00000"),
                metadata_json={},
            )
        ]
        risk_notes = [
            SignalRiskNote(
                code="no_profile_candidates",
                message="No active strategy profiles were available for classification.",
                severity="high",
                metadata_json={},
            )
        ]
        return await self.signal_repository.create_signal(signal, [], evidence, risk_notes)

    async def persist_no_eligible_signal(
        self,
        run: AnalysisRun,
        candidates: list[PatternCandidate],
        rejections: list[RejectedCandidate],
        features: Mapping[str, Any] | None,
    ) -> Signal:
        for candidate in candidates:
            candidate.is_selected = False
        reason = dominant_rejection_reason(rejections)
        status = (
            SignalClassificationStatus.INSUFFICIENT_EVIDENCE
            if reason in {"low_data_quality", "insufficient_evidence"}
            else SignalClassificationStatus.NO_SIGNAL
        )
        signal = self.base_signal(
            run=run,
            classification_status=status,
            bias=SignalBias.NEUTRAL,
            confidence_score=Decimal("0.0000"),
            confidence_label=SignalConfidenceLabel.LOW,
            summary=(
                "No signal generated because no candidate passed deterministic "
                "profile filters."
            ),
            no_signal_reason=reason,
            features=features,
        )
        evidence = [
            SignalEvidence(
                evidence_type="classification",
                direction="neutral",
                message=rejection.message,
                numeric_value=rejection.candidate_strength,
                weight=Decimal("0.00000"),
                metadata_json={
                    "strategyProfileKey": rejection.profile_key,
                    "patternType": rejection.pattern_type,
                    "reasonCode": rejection.reason_code,
                },
            )
            for rejection in rejections[:25]
        ]
        risk_notes = [
            SignalRiskNote(
                code=reason,
                message="No candidate passed deterministic strategy profile filters.",
                severity="medium",
                metadata_json={},
            )
        ]
        return await self.signal_repository.create_signal(signal, [], evidence, risk_notes)

    def build_signal(
        self,
        run: AnalysisRun,
        classification_status: SignalClassificationStatus,
        bias: SignalBias,
        no_signal_reason: str | None,
        summary: str,
        selected_evaluation: CandidateEvaluation | None,
        features: Mapping[str, Any] | None,
    ) -> Signal:
        if selected_evaluation is None:
            return self.base_signal(
                run=run,
                classification_status=classification_status,
                bias=bias,
                confidence_score=Decimal("0.0000"),
                confidence_label=SignalConfidenceLabel.LOW,
                summary=summary,
                no_signal_reason=no_signal_reason,
                features=features,
            )
        return self.base_signal(
            run=run,
            classification_status=classification_status,
            bias=bias,
            confidence_score=selected_evaluation.confidence.confidence_score,
            confidence_label=selected_evaluation.confidence.confidence_label,
            summary=summary,
            no_signal_reason=no_signal_reason,
            features=features,
            selected_evaluation=selected_evaluation,
        )

    def base_signal(
        self,
        run: AnalysisRun,
        classification_status: SignalClassificationStatus,
        bias: SignalBias,
        confidence_score: Decimal,
        confidence_label: SignalConfidenceLabel,
        summary: str,
        no_signal_reason: str | None,
        features: Mapping[str, Any] | None,
        selected_evaluation: CandidateEvaluation | None = None,
    ) -> Signal:
        candidate = selected_evaluation.candidate if selected_evaluation is not None else None
        profile = selected_evaluation.profile if selected_evaluation is not None else None
        return Signal(
            analysis_run_id=run.id,
            workspace_id=run.workspace_id,
            symbol_id=run.symbol_id,
            timeframe=run.timeframe,
            strategy_profile_id=profile.id if profile is not None else None,
            strategy_profile_key=profile.key if profile is not None else None,
            strategy_profile_version=profile.version if profile is not None else None,
            strategy_profile_snapshot_json=(
                profile_snapshot(profile) if profile is not None else None
            ),
            bias=bias.value,
            pattern_type=candidate.pattern_type if candidate is not None else None,
            classification_status=classification_status.value,
            confidence_score=confidence_score,
            confidence_label=confidence_label.value,
            candidate_strength=candidate.strength_score if candidate is not None else None,
            selected_pattern_candidate_id=candidate.id if candidate is not None else None,
            pips_moved=decimal_feature(features, "movement", "pipsMoved"),
            tick_moved=decimal_feature(features, "movement", "ticksMoved"),
            movement_direction=string_feature(features, "movement", "netDirection"),
            movement_quality=movement_quality(features),
            volatility_state=string_feature(features, "volatility", "volatilityState"),
            trend_state=string_feature(features, "trend", "trendState"),
            range_state=string_feature(features, "range", "rangeState"),
            summary=summary,
            no_signal_reason=no_signal_reason,
        )

    def build_confidence_components(
        self,
        selected_evaluation: CandidateEvaluation | None,
    ) -> list[SignalConfidenceComponent]:
        if selected_evaluation is None:
            return []
        return [
            SignalConfidenceComponent(
                component_name=component.component_name,
                component_score=component.component_score,
                component_weight=component.component_weight,
                weighted_score=component.weighted_score,
                reason=component.reason,
            )
            for component in selected_evaluation.confidence.components
        ]

    def build_evidence(
        self,
        selected_evaluation: CandidateEvaluation | None,
        decision_evidence: tuple[dict[str, object], ...],
    ) -> list[SignalEvidence]:
        evidence_rows: list[SignalEvidence] = []
        if selected_evaluation is not None:
            evidence_rows.extend(candidate_evidence_rows(selected_evaluation.candidate))
            evidence_rows.extend(
                classifier_evidence_rows(selected_evaluation.classifier_evidence)
            )
        evidence_rows.extend(classifier_evidence_rows(decision_evidence))
        return evidence_rows

    def build_risk_notes(
        self,
        selected_evaluation: CandidateEvaluation | None,
        decision_risk_notes: tuple[dict[str, object], ...],
    ) -> list[SignalRiskNote]:
        notes: list[SignalRiskNote] = []
        if selected_evaluation is not None:
            notes.extend(candidate_risk_note_rows(selected_evaluation.candidate))
            notes.extend(risk_note_rows(selected_evaluation.risk_notes))
        notes.extend(risk_note_rows(decision_risk_notes))
        return notes

    async def add_audit_log(
        self,
        analysis_run_id: UUID,
        event_type: str,
        message: str,
        metadata_json: dict[str, object] | None = None,
    ) -> AnalysisAuditLog:
        return await self.analysis_repository.add_audit_log(
            AnalysisAuditLog(
                analysis_run_id=analysis_run_id,
                event_type=event_type,
                message=message,
                metadata_json=metadata_json,
            )
        )


def rejected_candidate(
    profile: StrategyProfile,
    candidate: PatternCandidate,
    reason_code: str,
    message: str,
) -> RejectedCandidate:
    return RejectedCandidate(
        profile_key=profile.key,
        pattern_type=candidate.pattern_type,
        reason_code=reason_code,
        message=message,
        candidate_strength=candidate.strength_score,
    )


def dominant_rejection_reason(rejections: list[RejectedCandidate]) -> str:
    if not rejections:
        return "no_profile_candidates"
    priority = [
        "low_data_quality",
        "below_minimum_confidence",
        "below_minimum_strength",
        "insufficient_evidence",
        "unsupported_pattern_type",
    ]
    reason_counts = {reason: 0 for reason in priority}
    for rejection in rejections:
        if rejection.reason_code in reason_counts:
            reason_counts[rejection.reason_code] += 1
    for reason in priority:
        if reason_counts[reason] > 0:
            return reason
    return rejections[0].reason_code


def profile_snapshot(profile: StrategyProfile) -> dict[str, object]:
    return {
        "key": profile.key,
        "name": profile.name,
        "description": profile.description,
        "version": profile.version,
        "isActive": profile.is_active,
        "allowedPatterns": profile.allowed_patterns_json,
        "excludedPatterns": profile.excluded_patterns_json,
        "minimumCandidateStrength": str(profile.minimum_candidate_strength),
        "minimumConfidence": str(profile.minimum_confidence),
        "componentWeights": profile.component_weights_json,
        "riskFilters": profile.risk_filters_json,
        "noSignalRules": profile.no_signal_rules_json,
    }


def movement_quality(features: Mapping[str, Any] | None) -> str | None:
    efficiency = decimal_feature(features, "movement", "movementEfficiency")
    if efficiency is None:
        return None
    if efficiency < Decimal("0.2500"):
        return "choppy"
    if efficiency < Decimal("0.5000"):
        return "mixed"
    return "efficient"


def candidate_evidence_rows(candidate: PatternCandidate) -> list[SignalEvidence]:
    rows: list[SignalEvidence] = []
    for item in candidate.evidence_json:
        name = str(item.get("name", "pattern_evidence"))
        passed = item.get("passed") is True
        direction = f"supports_{candidate.bias}" if passed else "contradicts_signal"
        value = item.get("value")
        threshold = item.get("threshold")
        metadata = serialize_pattern_map(
            {
                "patternCandidateId": str(candidate.id),
                "patternType": candidate.pattern_type,
                "passed": passed,
                "value": value,
                "threshold": threshold,
            }
        )
        rows.append(
            SignalEvidence(
                evidence_type="pattern_candidate",
                direction=direction,
                message=f"Pattern evidence {name} {'passed' if passed else 'did not pass'}.",
                numeric_value=decimal_value(value),
                weight=decimal_value(item.get("weight")) or Decimal("0.00000"),
                metadata_json=metadata,
            )
        )
    return rows


def classifier_evidence_rows(items: tuple[dict[str, object], ...]) -> list[SignalEvidence]:
    rows: list[SignalEvidence] = []
    for item in items:
        metadata = item.get("metadata")
        metadata_json = metadata if isinstance(metadata, Mapping) else {}
        rows.append(
            SignalEvidence(
                evidence_type=str(item.get("evidence_type", "classification")),
                direction=str(item.get("direction", "neutral")),
                message=str(item.get("message", "Deterministic classifier evidence.")),
                numeric_value=decimal_value(item.get("numeric_value")),
                weight=decimal_value(item.get("weight")) or Decimal("0.00000"),
                metadata_json=serialize_pattern_map(dict(metadata_json)),
            )
        )
    return rows


def candidate_risk_note_rows(candidate: PatternCandidate) -> list[SignalRiskNote]:
    rows: list[SignalRiskNote] = []
    for item in candidate.risk_notes_json:
        rows.append(
            SignalRiskNote(
                code=str(item.get("code", "candidate_risk_note")),
                message=str(item.get("message", "Candidate risk note.")),
                severity=normalize_severity(item.get("severity")),
                metadata_json=serialize_pattern_map(
                    {
                        "patternCandidateId": str(candidate.id),
                        "patternType": candidate.pattern_type,
                    }
                ),
            )
        )
    return rows


def risk_note_rows(items: tuple[dict[str, object], ...]) -> list[SignalRiskNote]:
    rows: list[SignalRiskNote] = []
    for item in items:
        metadata = item.get("metadata")
        metadata_json = metadata if isinstance(metadata, Mapping) else {}
        rows.append(
            SignalRiskNote(
                code=str(item.get("code", "classification_risk_note")),
                message=str(item.get("message", "Classification risk note.")),
                severity=normalize_severity(item.get("severity")),
                metadata_json=serialize_pattern_map(dict(metadata_json)),
            )
        )
    return rows


def normalize_severity(value: object) -> str:
    if isinstance(value, str) and value in {"info", "low", "medium", "high", "critical"}:
        return value
    return "medium"
