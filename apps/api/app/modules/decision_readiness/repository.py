from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.decision_readiness.models import DecisionReadinessAssessment
from app.modules.explanations.models import DeterministicExplanation
from app.modules.llm_explanations.models import LlmExplanation
from app.modules.news.models import SignalNewsCorrelation
from app.modules.outcomes.models import SignalOutcome
from app.modules.profile_diagnostics.models import (
    PatternOutcomeDiagnostic,
    StrategyProfileDiagnostic,
)
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)


class DecisionReadinessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_signal(self, signal_id: UUID) -> Signal | None:
        return await self.session.get(Signal, signal_id)

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        return await self.session.get(AnalysisRun, analysis_run_id)

    async def get_signal_by_analysis_run_id(self, analysis_run_id: UUID) -> Signal | None:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(Signal.analysis_run_id == analysis_run_id)
            .order_by(Signal.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_by_source_version(
        self,
        source_type: str,
        source_id: UUID,
        assessment_version: str,
    ) -> DecisionReadinessAssessment | None:
        statement: Select[tuple[DecisionReadinessAssessment]] = select(
            DecisionReadinessAssessment
        ).where(
            DecisionReadinessAssessment.source_type == source_type,
            DecisionReadinessAssessment.source_id == source_id,
            DecisionReadinessAssessment.assessment_version == assessment_version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_for_signal(
        self,
        signal_id: UUID,
    ) -> DecisionReadinessAssessment | None:
        statement: Select[tuple[DecisionReadinessAssessment]] = (
            select(DecisionReadinessAssessment)
            .where(DecisionReadinessAssessment.signal_id == signal_id)
            .order_by(DecisionReadinessAssessment.updated_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_for_analysis_run(
        self,
        analysis_run_id: UUID,
    ) -> DecisionReadinessAssessment | None:
        statement: Select[tuple[DecisionReadinessAssessment]] = (
            select(DecisionReadinessAssessment)
            .where(DecisionReadinessAssessment.analysis_run_id == analysis_run_id)
            .order_by(DecisionReadinessAssessment.updated_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_assessments(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        readiness_label: str | None = None,
        source_type: str | None = None,
        signal_id: UUID | None = None,
        analysis_run_id: UUID | None = None,
    ) -> list[DecisionReadinessAssessment]:
        statement: Select[tuple[DecisionReadinessAssessment]] = (
            select(DecisionReadinessAssessment)
            .where(DecisionReadinessAssessment.workspace_id == workspace_id)
            .order_by(DecisionReadinessAssessment.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if readiness_label is not None:
            statement = statement.where(DecisionReadinessAssessment.readiness_label == readiness_label)
        if source_type is not None:
            statement = statement.where(DecisionReadinessAssessment.source_type == source_type)
        if signal_id is not None:
            statement = statement.where(DecisionReadinessAssessment.signal_id == signal_id)
        if analysis_run_id is not None:
            statement = statement.where(DecisionReadinessAssessment.analysis_run_id == analysis_run_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def upsert_assessment(
        self,
        assessment: DecisionReadinessAssessment,
        force_recompute: bool,
    ) -> DecisionReadinessAssessment:
        existing = await self.get_by_source_version(
            assessment.source_type,
            assessment.source_id,
            assessment.assessment_version,
        )
        if existing is None:
            self.session.add(assessment)
            await self.session.flush()
            await self.session.refresh(assessment)
            return assessment
        if not force_recompute:
            return existing
        copy_assessment_values(assessment, existing)
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def list_confidence_components(
        self,
        signal_id: UUID,
    ) -> list[SignalConfidenceComponent]:
        statement: Select[tuple[SignalConfidenceComponent]] = (
            select(SignalConfidenceComponent)
            .where(SignalConfidenceComponent.signal_id == signal_id)
            .order_by(SignalConfidenceComponent.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_evidence(self, signal_id: UUID) -> list[SignalEvidence]:
        statement: Select[tuple[SignalEvidence]] = (
            select(SignalEvidence)
            .where(SignalEvidence.signal_id == signal_id)
            .order_by(SignalEvidence.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_risk_notes(self, signal_id: UUID) -> list[SignalRiskNote]:
        statement: Select[tuple[SignalRiskNote]] = (
            select(SignalRiskNote)
            .where(SignalRiskNote.signal_id == signal_id)
            .order_by(SignalRiskNote.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_deterministic_explanation(
        self,
        signal_id: UUID,
    ) -> DeterministicExplanation | None:
        statement: Select[tuple[DeterministicExplanation]] = select(
            DeterministicExplanation
        ).where(DeterministicExplanation.signal_id == signal_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_llm_explanation(self, signal_id: UUID) -> LlmExplanation | None:
        statement: Select[tuple[LlmExplanation]] = (
            select(LlmExplanation)
            .where(LlmExplanation.signal_id == signal_id)
            .order_by(LlmExplanation.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_news_correlations(self, signal_id: UUID) -> list[SignalNewsCorrelation]:
        statement: Select[tuple[SignalNewsCorrelation]] = (
            select(SignalNewsCorrelation)
            .where(SignalNewsCorrelation.signal_id == signal_id)
            .order_by(SignalNewsCorrelation.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_outcomes(self, signal_id: UUID) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.signal_id == signal_id)
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_reasoning_runs(
        self,
        signal_id: UUID | None,
        analysis_run_id: UUID | None,
    ) -> list[LlmReasoningRun]:
        conditions = []
        if signal_id is not None:
            conditions.append(LlmReasoningRun.signal_id == signal_id)
        if analysis_run_id is not None:
            conditions.append(LlmReasoningRun.analysis_run_id == analysis_run_id)
        if not conditions:
            return []
        statement: Select[tuple[LlmReasoningRun]] = (
            select(LlmReasoningRun)
            .where(or_(*conditions))
            .order_by(LlmReasoningRun.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_scenario_hypotheses(
        self,
        reasoning_run_ids: list[UUID],
    ) -> list[ScenarioHypothesis]:
        if not reasoning_run_ids:
            return []
        statement: Select[tuple[ScenarioHypothesis]] = (
            select(ScenarioHypothesis)
            .where(ScenarioHypothesis.reasoning_run_id.in_(reasoning_run_ids))
            .order_by(ScenarioHypothesis.sort_order.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_action_plans(
        self,
        signal_id: UUID | None,
        analysis_run_id: UUID | None,
    ) -> list[ReasoningActionPlan]:
        conditions = []
        if signal_id is not None:
            conditions.append(ReasoningActionPlan.signal_id == signal_id)
        if analysis_run_id is not None:
            conditions.append(ReasoningActionPlan.analysis_run_id == analysis_run_id)
        if not conditions:
            return []
        statement: Select[tuple[ReasoningActionPlan]] = (
            select(ReasoningActionPlan)
            .where(or_(*conditions))
            .order_by(ReasoningActionPlan.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_open_action_items(
        self,
        signal_id: UUID | None,
        analysis_run_id: UUID | None,
    ) -> list[ReasoningActionItem]:
        conditions = []
        if signal_id is not None:
            conditions.append(ReasoningActionItem.signal_id == signal_id)
        if analysis_run_id is not None:
            conditions.append(ReasoningActionItem.analysis_run_id == analysis_run_id)
        if not conditions:
            return []
        statement: Select[tuple[ReasoningActionItem]] = (
            select(ReasoningActionItem)
            .where(
                and_(
                    or_(*conditions),
                    ReasoningActionItem.status.in_(["pending", "due", "running"]),
                )
            )
            .order_by(ReasoningActionItem.due_at.asc().nullslast())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_audit_logs(self, analysis_run_id: UUID | None) -> list[AnalysisAuditLog]:
        if analysis_run_id is None:
            return []
        statement: Select[tuple[AnalysisAuditLog]] = (
            select(AnalysisAuditLog)
            .where(AnalysisAuditLog.analysis_run_id == analysis_run_id)
            .order_by(AnalysisAuditLog.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_chart_screenshot_runs(
        self,
        analysis_run_id: UUID | None,
    ) -> list[ChartScreenshotRun]:
        if analysis_run_id is None:
            return []
        statement: Select[tuple[ChartScreenshotRun]] = (
            select(ChartScreenshotRun)
            .where(ChartScreenshotRun.analysis_run_id == analysis_run_id)
            .order_by(ChartScreenshotRun.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_profile_diagnostics(self, signal: Signal | None) -> int:
        if signal is None:
            return 0
        conditions = [StrategyProfileDiagnostic.workspace_id == signal.workspace_id]
        if signal.strategy_profile_key is not None:
            conditions.append(StrategyProfileDiagnostic.strategy_profile_key == signal.strategy_profile_key)
        statement = select(func.count()).select_from(StrategyProfileDiagnostic).where(and_(*conditions))
        result = await self.session.execute(statement)
        strategy_count = int(result.scalar_one())
        pattern_count = 0
        if signal.pattern_type is not None:
            pattern_statement = (
                select(func.count())
                .select_from(PatternOutcomeDiagnostic)
                .where(
                    PatternOutcomeDiagnostic.workspace_id == signal.workspace_id,
                    PatternOutcomeDiagnostic.pattern_type == signal.pattern_type,
                )
            )
            pattern_result = await self.session.execute(pattern_statement)
            pattern_count = int(pattern_result.scalar_one())
        return strategy_count + pattern_count

    async def list_quality_findings(
        self,
        signal_id: UUID | None,
        analysis_run_id: UUID | None,
    ) -> list[dict[str, object]]:
        return []

    async def list_operator_reviews(
        self,
        signal_id: UUID | None,
        analysis_run_id: UUID | None,
    ) -> list[dict[str, object]]:
        return []

    async def list_historical_cases(
        self,
        signal: Signal | None,
    ) -> list[dict[str, object]]:
        return []

    def utc_now(self) -> datetime:
        return datetime.now(UTC)


def copy_assessment_values(
    source: DecisionReadinessAssessment,
    target: DecisionReadinessAssessment,
) -> None:
    target.workspace_id = source.workspace_id
    target.analysis_run_id = source.analysis_run_id
    target.signal_id = source.signal_id
    target.readiness_score = source.readiness_score
    target.readiness_label = source.readiness_label
    target.status = source.status
    target.required_checks_json = source.required_checks_json
    target.optional_checks_json = source.optional_checks_json
    target.blockers_json = source.blockers_json
    target.warnings_json = source.warnings_json
    target.next_steps_json = source.next_steps_json
    target.summary = source.summary
    target.metadata_json = source.metadata_json
