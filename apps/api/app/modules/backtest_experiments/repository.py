from uuid import UUID

from sqlalchemy import Select, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.backtest_experiments.cohort import BacktestOutcomeRow
from app.modules.backtest_experiments.models import (
    BacktestExperimentCohort,
    BacktestExperimentRun,
)
from app.modules.backtest_experiments.schemas import BacktestExperimentFilters
from app.modules.news.models import SignalNewsCorrelation
from app.modules.outcomes.models import SignalOutcome
from app.modules.signals.models import Signal


class BacktestExperimentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: BacktestExperimentRun) -> BacktestExperimentRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> BacktestExperimentRun | None:
        return await self.session.get(BacktestExperimentRun, run_id)

    async def list_runs(
        self,
        workspace_id: UUID,
        limit: int,
        status: str | None = None,
    ) -> list[BacktestExperimentRun]:
        statement: Select[tuple[BacktestExperimentRun]] = (
            select(BacktestExperimentRun)
            .where(BacktestExperimentRun.workspace_id == workspace_id)
            .order_by(BacktestExperimentRun.created_at.desc())
            .limit(limit)
        )
        if status is not None:
            statement = statement.where(BacktestExperimentRun.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_cohorts(
        self,
        cohorts: list[BacktestExperimentCohort],
    ) -> list[BacktestExperimentCohort]:
        self.session.add_all(cohorts)
        await self.session.flush()
        for cohort in cohorts:
            await self.session.refresh(cohort)
        return cohorts

    async def list_cohorts(self, run_id: UUID) -> list[BacktestExperimentCohort]:
        statement: Select[tuple[BacktestExperimentCohort]] = (
            select(BacktestExperimentCohort)
            .where(BacktestExperimentCohort.experiment_run_id == run_id)
            .order_by(
                BacktestExperimentCohort.horizon_minutes.asc(),
                BacktestExperimentCohort.cohort_key.asc(),
            )
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_outcome_rows(
        self,
        workspace_id: UUID,
        horizons_minutes: list[int],
        filters: BacktestExperimentFilters,
    ) -> list[BacktestOutcomeRow]:
        statement: Select[tuple[Signal, SignalOutcome]] = (
            select(Signal, SignalOutcome)
            .join(SignalOutcome, SignalOutcome.signal_id == Signal.id)
            .where(
                Signal.workspace_id == workspace_id,
                SignalOutcome.workspace_id == workspace_id,
                SignalOutcome.horizon_minutes.in_(horizons_minutes),
            )
            .order_by(SignalOutcome.reference_time.asc(), SignalOutcome.created_at.asc())
            .limit(filters.limit)
        )
        if filters.strategy_profile_key is not None:
            statement = statement.where(Signal.strategy_profile_key == filters.strategy_profile_key)
        if filters.symbol_id is not None:
            statement = statement.where(Signal.symbol_id == filters.symbol_id)
        if filters.timeframe is not None:
            statement = statement.where(Signal.timeframe == filters.timeframe)
        if filters.start_time is not None:
            statement = statement.where(SignalOutcome.reference_time >= filters.start_time)
        if filters.end_time is not None:
            statement = statement.where(SignalOutcome.reference_time <= filters.end_time)
        result = await self.session.execute(statement)
        pairs = list(result.all())
        correlation_labels = await self.news_correlation_labels(
            [signal.id for signal, _outcome in pairs]
        )
        return [
            BacktestOutcomeRow(
                signal=signal,
                outcome=outcome,
                news_correlation_label=correlation_labels.get(signal.id),
            )
            for signal, outcome in pairs
        ]

    async def news_correlation_labels(self, signal_ids: list[UUID]) -> dict[UUID, str]:
        unique_signal_ids = list({signal_id for signal_id in signal_ids})
        if not unique_signal_ids:
            return {}
        statement = select(
            SignalNewsCorrelation.signal_id,
            SignalNewsCorrelation.correlation_label,
        ).where(SignalNewsCorrelation.signal_id.in_(unique_signal_ids))
        result = await self.session.execute(statement)
        label_rank = {"none": 0, "weak": 1, "possible": 2, "strong": 3}
        labels: dict[UUID, str] = {}
        for signal_id, label in result.all():
            existing = labels.get(signal_id)
            if existing is None or label_rank.get(label, 0) > label_rank.get(existing, 0):
                labels[signal_id] = label
        return labels

    async def count_distinct_signals_for_rows(self, rows: list[BacktestOutcomeRow]) -> int:
        if not rows:
            return 0
        signal_ids = {row.signal.id for row in rows}
        statement = select(distinct(Signal.id)).where(Signal.id.in_(signal_ids))
        result = await self.session.execute(statement)
        return len(result.scalars().all())
