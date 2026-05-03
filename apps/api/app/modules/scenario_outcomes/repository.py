from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.news.models import SignalNewsCorrelation
from app.modules.outcomes.models import SignalOutcome
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.scenario_outcomes.models import (
    ScenarioHypothesisOutcome,
    ScenarioOutcomeSummaryRun,
)
from app.modules.scenario_outcomes.schemas import ScenarioOutcomeSummaryFilters


class ScenarioOutcomeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_hypothesis(self, scenario_hypothesis_id: UUID) -> ScenarioHypothesis | None:
        return await self.session.get(ScenarioHypothesis, scenario_hypothesis_id)

    async def get_reasoning_run(self, reasoning_run_id: UUID) -> LlmReasoningRun | None:
        return await self.session.get(LlmReasoningRun, reasoning_run_id)

    async def list_reasoning_hypotheses(self, reasoning_run_id: UUID) -> list[ScenarioHypothesis]:
        statement: Select[tuple[ScenarioHypothesis]] = (
            select(ScenarioHypothesis)
            .where(ScenarioHypothesis.reasoning_run_id == reasoning_run_id)
            .order_by(ScenarioHypothesis.sort_order.asc(), ScenarioHypothesis.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_signal_outcome_by_horizon(
        self,
        signal_id: UUID,
        horizon_minutes: int,
    ) -> SignalOutcome | None:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(
                SignalOutcome.signal_id == signal_id,
                SignalOutcome.horizon_minutes == horizon_minutes,
            )
            .order_by(SignalOutcome.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_signal_outcome_by_id(self, outcome_id: UUID) -> SignalOutcome | None:
        return await self.session.get(SignalOutcome, outcome_id)

    async def get_existing_hypothesis_outcome(
        self,
        scenario_hypothesis_id: UUID,
        horizon_minutes: int | None,
        evaluation_version: str,
    ) -> ScenarioHypothesisOutcome | None:
        statement: Select[tuple[ScenarioHypothesisOutcome]] = select(
            ScenarioHypothesisOutcome
        ).where(
            ScenarioHypothesisOutcome.scenario_hypothesis_id == scenario_hypothesis_id,
            ScenarioHypothesisOutcome.horizon_minutes == horizon_minutes,
            ScenarioHypothesisOutcome.evaluation_version == evaluation_version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_hypothesis_outcome(
        self,
        outcome: ScenarioHypothesisOutcome,
        force_recompute: bool,
    ) -> ScenarioHypothesisOutcome:
        existing = await self.get_existing_hypothesis_outcome(
            scenario_hypothesis_id=outcome.scenario_hypothesis_id,
            horizon_minutes=outcome.horizon_minutes,
            evaluation_version=outcome.evaluation_version,
        )
        if existing is None:
            self.session.add(outcome)
            await self.session.flush()
            await self.session.refresh(outcome)
            return outcome
        if not force_recompute:
            return existing
        copy_hypothesis_outcome_values(source=outcome, target=existing)
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def list_hypothesis_outcomes(
        self,
        reasoning_run_id: UUID,
    ) -> list[ScenarioHypothesisOutcome]:
        statement: Select[tuple[ScenarioHypothesisOutcome]] = (
            select(ScenarioHypothesisOutcome)
            .where(ScenarioHypothesisOutcome.reasoning_run_id == reasoning_run_id)
            .order_by(
                ScenarioHypothesisOutcome.horizon_minutes.asc().nulls_last(),
                ScenarioHypothesisOutcome.scenario_type.asc(),
                ScenarioHypothesisOutcome.created_at.asc(),
            )
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_news_contexts(self, signal_id: UUID) -> list[SignalNewsCorrelation]:
        statement: Select[tuple[SignalNewsCorrelation]] = (
            select(SignalNewsCorrelation)
            .where(SignalNewsCorrelation.signal_id == signal_id)
            .order_by(SignalNewsCorrelation.correlation_score.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_summary_run(
        self,
        run: ScenarioOutcomeSummaryRun,
    ) -> ScenarioOutcomeSummaryRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_summary_run(self, summary_run_id: UUID) -> ScenarioOutcomeSummaryRun | None:
        return await self.session.get(ScenarioOutcomeSummaryRun, summary_run_id)

    async def list_summary_outcomes(
        self,
        workspace_id: UUID,
        filters: ScenarioOutcomeSummaryFilters,
    ) -> list[ScenarioHypothesisOutcome]:
        statement: Select[tuple[ScenarioHypothesisOutcome]] = select(
            ScenarioHypothesisOutcome
        ).where(ScenarioHypothesisOutcome.workspace_id == workspace_id)
        if filters.provider is not None or filters.model is not None:
            statement = statement.join(
                LlmReasoningRun,
                LlmReasoningRun.id == ScenarioHypothesisOutcome.reasoning_run_id,
            )
        if filters.provider is not None:
            statement = statement.where(LlmReasoningRun.provider == filters.provider)
        if filters.model is not None:
            statement = statement.where(LlmReasoningRun.model == filters.model)
        if filters.scenario_type is not None:
            statement = statement.where(
                ScenarioHypothesisOutcome.scenario_type == filters.scenario_type
            )
        if filters.support_label is not None:
            statement = statement.where(
                ScenarioHypothesisOutcome.support_label == filters.support_label
            )
        if filters.reasoning_run_id is not None:
            statement = statement.where(
                ScenarioHypothesisOutcome.reasoning_run_id == filters.reasoning_run_id
            )
        if filters.signal_id is not None:
            statement = statement.where(ScenarioHypothesisOutcome.signal_id == filters.signal_id)
        if filters.horizon_minutes is not None:
            statement = statement.where(
                ScenarioHypothesisOutcome.horizon_minutes == filters.horizon_minutes
            )
        if filters.start_time is not None:
            statement = statement.where(ScenarioHypothesisOutcome.created_at >= filters.start_time)
        if filters.end_time is not None:
            statement = statement.where(ScenarioHypothesisOutcome.created_at <= filters.end_time)
        result = await self.session.execute(
            statement.order_by(ScenarioHypothesisOutcome.created_at.asc())
        )
        return list(result.scalars().all())


def copy_hypothesis_outcome_values(
    source: ScenarioHypothesisOutcome,
    target: ScenarioHypothesisOutcome,
) -> None:
    target.workspace_id = source.workspace_id
    target.reasoning_run_id = source.reasoning_run_id
    target.signal_id = source.signal_id
    target.analysis_run_id = source.analysis_run_id
    target.outcome_id = source.outcome_id
    target.horizon_minutes = source.horizon_minutes
    target.scenario_type = source.scenario_type
    target.possibility_label = source.possibility_label
    target.evaluation_status = source.evaluation_status
    target.support_label = source.support_label
    target.support_score = source.support_score
    target.matched_outcome_label = source.matched_outcome_label
    target.matched_evidence_json = source.matched_evidence_json
    target.conflicting_evidence_json = source.conflicting_evidence_json
    target.summary = source.summary
