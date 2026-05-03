from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.decision_readiness.calculator import (
    DecisionReadinessCalculator,
    DecisionReadinessContext,
    DecisionReadinessResult,
)
from app.modules.decision_readiness.models import (
    DecisionReadinessAssessment,
    DecisionReadinessSourceType,
    DecisionReadinessStatus,
)
from app.modules.decision_readiness.repository import DecisionReadinessRepository
from app.modules.decision_readiness.schemas import (
    DecisionReadinessAssessmentListResponse,
    DecisionReadinessAssessmentRead,
    DecisionReadinessAssessmentResponse,
    DecisionReadinessAssessmentSummary,
)
from app.modules.signals.models import Signal

ASSESSMENT_VERSION = "decision_readiness_v1"


class DecisionReadinessService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DecisionReadinessRepository(session)
        self.calculator = DecisionReadinessCalculator()

    async def assess_signal(
        self,
        signal_id: UUID,
        force_recompute: bool = False,
    ) -> DecisionReadinessAssessmentResponse:
        try:
            existing = await self.repository.get_by_source_version(
                DecisionReadinessSourceType.SIGNAL.value,
                signal_id,
                ASSESSMENT_VERSION,
            )
            if existing is not None and not force_recompute:
                return response_from_assessment(existing)
            signal = await self.repository.get_signal(signal_id)
            if signal is None:
                raise AppError(404, "signal_not_found", "Signal not found")
            context = await self.build_context(
                source_type=DecisionReadinessSourceType.SIGNAL.value,
                source_id=signal_id,
                signal=signal,
                analysis_run_id=signal.analysis_run_id,
            )
            assessment = await self.persist_assessment(context, force_recompute)
            await self.session.commit()
            return response_from_assessment(assessment)
        except Exception:
            await self.session.rollback()
            raise

    async def assess_analysis_run(
        self,
        analysis_run_id: UUID,
        force_recompute: bool = False,
    ) -> DecisionReadinessAssessmentResponse:
        try:
            existing = await self.repository.get_by_source_version(
                DecisionReadinessSourceType.ANALYSIS_RUN.value,
                analysis_run_id,
                ASSESSMENT_VERSION,
            )
            if existing is not None and not force_recompute:
                return response_from_assessment(existing)
            analysis_run = await self.repository.get_analysis_run(analysis_run_id)
            if analysis_run is None:
                raise AppError(404, "analysis_run_not_found", "Analysis run not found")
            signal = await self.repository.get_signal_by_analysis_run_id(analysis_run_id)
            context = await self.build_context(
                source_type=DecisionReadinessSourceType.ANALYSIS_RUN.value,
                source_id=analysis_run_id,
                signal=signal,
                analysis_run_id=analysis_run_id,
            )
            assessment = await self.persist_assessment(context, force_recompute)
            await self.session.commit()
            return response_from_assessment(assessment)
        except Exception:
            await self.session.rollback()
            raise

    async def get_latest_for_signal(
        self,
        signal_id: UUID,
    ) -> DecisionReadinessAssessmentResponse:
        signal = await self.repository.get_signal(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        assessment = await self.repository.get_latest_for_signal(signal_id)
        if assessment is None:
            raise AppError(
                404,
                "decision_readiness_assessment_not_found",
                "Decision readiness assessment not found",
            )
        return response_from_assessment(assessment)

    async def get_latest_for_analysis_run(
        self,
        analysis_run_id: UUID,
    ) -> DecisionReadinessAssessmentResponse:
        analysis_run = await self.repository.get_analysis_run(analysis_run_id)
        if analysis_run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        assessment = await self.repository.get_latest_for_analysis_run(analysis_run_id)
        if assessment is None:
            raise AppError(
                404,
                "decision_readiness_assessment_not_found",
                "Decision readiness assessment not found",
            )
        return response_from_assessment(assessment)

    async def list_assessments(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        readiness_label: str | None = None,
        source_type: str | None = None,
        signal_id: UUID | None = None,
        analysis_run_id: UUID | None = None,
    ) -> DecisionReadinessAssessmentListResponse:
        assessments = await self.repository.list_assessments(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
            readiness_label=readiness_label,
            source_type=source_type,
            signal_id=signal_id,
            analysis_run_id=analysis_run_id,
        )
        return DecisionReadinessAssessmentListResponse(
            assessments=[
                DecisionReadinessAssessmentRead.model_validate(assessment)
                for assessment in assessments
            ]
        )

    async def build_context(
        self,
        source_type: str,
        source_id: UUID,
        signal: Signal | None,
        analysis_run_id: UUID | None,
    ) -> DecisionReadinessContext:
        analysis_run = (
            await self.repository.get_analysis_run(analysis_run_id)
            if analysis_run_id is not None
            else None
        )
        signal_id = signal.id if signal is not None else None
        reasoning_runs = await self.repository.list_reasoning_runs(
            signal_id=signal_id,
            analysis_run_id=analysis_run_id,
        )
        return DecisionReadinessContext(
            source_type=source_type,
            source_id=source_id,
            signal=signal,
            analysis_run=analysis_run,
            evidence=await self.repository.list_evidence(signal_id) if signal_id else [],
            confidence_components=(
                await self.repository.list_confidence_components(signal_id)
                if signal_id
                else []
            ),
            risk_notes=await self.repository.list_risk_notes(signal_id) if signal_id else [],
            deterministic_explanation=(
                await self.repository.get_deterministic_explanation(signal_id)
                if signal_id
                else None
            ),
            llm_explanation=(
                await self.repository.get_latest_llm_explanation(signal_id)
                if signal_id
                else None
            ),
            news_correlations=(
                await self.repository.list_news_correlations(signal_id) if signal_id else []
            ),
            outcomes=await self.repository.list_outcomes(signal_id) if signal_id else [],
            reasoning_runs=reasoning_runs,
            scenario_hypotheses=await self.repository.list_scenario_hypotheses(
                [run.id for run in reasoning_runs]
            ),
            action_plans=await self.repository.list_action_plans(signal_id, analysis_run_id),
            open_action_items=await self.repository.list_open_action_items(
                signal_id,
                analysis_run_id,
            ),
            audit_logs=await self.repository.list_audit_logs(analysis_run_id),
            chart_screenshot_runs=await self.repository.list_chart_screenshot_runs(
                analysis_run_id
            ),
            profile_diagnostics_count=await self.repository.count_profile_diagnostics(signal),
            historical_cases_count=len(await self.repository.list_historical_cases(signal)),
            quality_findings=await self.repository.list_quality_findings(
                signal_id,
                analysis_run_id,
            ),
            operator_reviews=await self.repository.list_operator_reviews(
                signal_id,
                analysis_run_id,
            ),
        )

    async def persist_assessment(
        self,
        context: DecisionReadinessContext,
        force_recompute: bool,
    ) -> DecisionReadinessAssessment:
        result = self.calculator.calculate(context)
        workspace_id = resolve_workspace_id(context)
        assessment = build_assessment(context, result, workspace_id)
        return await self.repository.upsert_assessment(assessment, force_recompute)


def resolve_workspace_id(context: DecisionReadinessContext) -> UUID:
    if context.signal is not None:
        return context.signal.workspace_id
    if context.analysis_run is not None:
        return context.analysis_run.workspace_id
    raise AppError(422, "workspace_context_missing", "Workspace context is missing")


def build_assessment(
    context: DecisionReadinessContext,
    result: DecisionReadinessResult,
    workspace_id: UUID,
) -> DecisionReadinessAssessment:
    return DecisionReadinessAssessment(
        workspace_id=workspace_id,
        source_type=context.source_type,
        source_id=context.source_id,
        analysis_run_id=context.analysis_run.id if context.analysis_run else None,
        signal_id=context.signal.id if context.signal else None,
        assessment_version=ASSESSMENT_VERSION,
        readiness_score=result.readiness_score,
        readiness_label=result.readiness_label,
        status=DecisionReadinessStatus.COMPLETED.value,
        required_checks_json=result.required_checks,
        optional_checks_json=result.optional_checks,
        blockers_json=result.blockers,
        warnings_json=result.warnings,
        next_steps_json=result.next_steps,
        summary=result.summary,
        metadata_json=result.metadata,
    )


def response_from_assessment(
    assessment: DecisionReadinessAssessment,
) -> DecisionReadinessAssessmentResponse:
    return DecisionReadinessAssessmentResponse(
        assessment=DecisionReadinessAssessmentSummary(
            readiness_score=float(assessment.readiness_score),
            readiness_label=assessment.readiness_label,
            summary=assessment.summary,
        ),
        blockers=assessment.blockers_json,
        warnings=assessment.warnings_json,
        next_steps=assessment.next_steps_json,
    )
