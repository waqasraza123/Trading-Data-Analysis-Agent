from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.analysis.models import AnalysisAuditLog
from app.modules.analysis.repository import AnalysisRepository
from app.modules.explanations.models import DeterministicExplanation, ExplanationSafetyStatus
from app.modules.explanations.repository import DeterministicExplanationRepository
from app.modules.explanations.safety import check_explanation_safety
from app.modules.explanations.schemas import DeterministicExplanationRead
from app.modules.explanations.templates import (
    FALLBACK_EXPLANATION,
    ExplanationDraft,
    build_explanation_draft,
)
from app.modules.features.repository import FeatureSnapshotRepository
from app.modules.indicators.repository import IndicatorSnapshotRepository
from app.modules.signals.models import Signal
from app.modules.signals.repository import SignalRepository


class DeterministicExplanationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DeterministicExplanationRepository(session)
        self.signal_repository = SignalRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.feature_repository = FeatureSnapshotRepository(session)
        self.indicator_repository = IndicatorSnapshotRepository(session)

    async def generate_for_signal_id(
        self,
        signal_id: UUID,
        commit: bool = True,
    ) -> DeterministicExplanationRead:
        try:
            signal = await self.signal_repository.get_by_id(signal_id)
            if signal is None:
                raise AppError(404, "signal_not_found", "Signal not found")
            explanation = await self.generate_for_signal(signal)
            if commit:
                await self.session.commit()
            return DeterministicExplanationRead.model_validate(explanation)
        except Exception:
            if commit:
                await self.session.rollback()
            raise

    async def generate_for_analysis_run_id(
        self,
        analysis_run_id: UUID,
        commit: bool = True,
    ) -> DeterministicExplanationRead:
        signal = await self.signal_repository.get_by_analysis_run_id(analysis_run_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return await self.generate_for_signal_id(signal.id, commit=commit)

    async def get_by_signal_id(self, signal_id: UUID) -> DeterministicExplanationRead:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        explanation = await self.repository.get_by_signal_id(signal_id)
        if explanation is None:
            raise AppError(
                404,
                "deterministic_explanation_not_found",
                "Deterministic explanation not found",
            )
        return DeterministicExplanationRead.model_validate(explanation)

    async def get_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> DeterministicExplanationRead:
        run = await self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        explanation = await self.repository.get_by_analysis_run_id(analysis_run_id)
        if explanation is None:
            raise AppError(
                404,
                "deterministic_explanation_not_found",
                "Deterministic explanation not found",
            )
        return DeterministicExplanationRead.model_validate(explanation)

    async def get_optional_by_signal_id(
        self,
        signal_id: UUID,
    ) -> DeterministicExplanationRead | None:
        explanation = await self.repository.get_by_signal_id(signal_id)
        if explanation is None:
            return None
        return DeterministicExplanationRead.model_validate(explanation)

    async def generate_for_signal(self, signal: Signal) -> DeterministicExplanation:
        await self.add_audit_log(
            signal.analysis_run_id,
            "deterministic_explanation_started",
            "Deterministic explanation generation started",
            {"signalId": str(signal.id)},
        )
        try:
            confidence_components = await self.signal_repository.list_confidence_components(
                signal.id
            )
            evidence = await self.signal_repository.list_evidence(signal.id)
            risk_notes = await self.signal_repository.list_risk_notes(signal.id)
            feature_snapshot = await self.feature_repository.get_by_analysis_run_id(
                signal.analysis_run_id
            )
            indicator_snapshot = await self.indicator_repository.get_by_analysis_run_id(
                signal.analysis_run_id
            )
            draft = build_explanation_draft(
                signal=signal,
                confidence_components=confidence_components,
                evidence=evidence,
                risk_notes=risk_notes,
                feature_snapshot=feature_snapshot,
                indicator_snapshot=indicator_snapshot,
            )
            explanation = await self.repository.upsert_for_signal(
                build_explanation_model(signal, draft)
            )
            if explanation.safety_status == ExplanationSafetyStatus.BLOCKED:
                await self.add_audit_log(
                    signal.analysis_run_id,
                    "deterministic_explanation_blocked",
                    "Deterministic explanation used safety fallback",
                    {
                        "signalId": str(signal.id),
                        "blockedTerms": explanation.blocked_terms_json,
                    },
                )
            else:
                await self.add_audit_log(
                    signal.analysis_run_id,
                    "deterministic_explanation_generated",
                    "Deterministic explanation generated",
                    {"signalId": str(signal.id), "explanationId": str(explanation.id)},
                )
            return explanation
        except Exception:
            await self.add_audit_log(
                signal.analysis_run_id,
                "deterministic_explanation_failed",
                "Deterministic explanation generation failed",
                {"signalId": str(signal.id)},
            )
            raise

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


def build_explanation_model(signal: Signal, draft: ExplanationDraft) -> DeterministicExplanation:
    safety_result = check_explanation_safety(draft.full_text)
    if not safety_result.passed:
        return DeterministicExplanation(
            signal_id=signal.id,
            analysis_run_id=signal.analysis_run_id,
            workspace_id=signal.workspace_id,
            template_version=draft.template_version,
            explanation_type=draft.explanation_type.value,
            short_summary=FALLBACK_EXPLANATION,
            market_behavior=FALLBACK_EXPLANATION,
            evidence_summary=FALLBACK_EXPLANATION,
            confidence_summary=FALLBACK_EXPLANATION,
            risk_summary=FALLBACK_EXPLANATION,
            no_signal_summary=None,
            full_text=FALLBACK_EXPLANATION,
            source_snapshot_json=draft.source_snapshot_json,
            safety_status=ExplanationSafetyStatus.BLOCKED.value,
            blocked_terms_json=safety_result.blocked_terms,
        )
    return DeterministicExplanation(
        signal_id=signal.id,
        analysis_run_id=signal.analysis_run_id,
        workspace_id=signal.workspace_id,
        template_version=draft.template_version,
        explanation_type=draft.explanation_type.value,
        short_summary=draft.short_summary,
        market_behavior=draft.market_behavior,
        evidence_summary=draft.evidence_summary,
        confidence_summary=draft.confidence_summary,
        risk_summary=draft.risk_summary,
        no_signal_summary=draft.no_signal_summary,
        full_text=draft.full_text,
        source_snapshot_json=draft.source_snapshot_json,
        safety_status=ExplanationSafetyStatus.PASSED.value,
        blocked_terms_json=[],
    )
