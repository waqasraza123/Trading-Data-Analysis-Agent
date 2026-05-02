from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.backtest_experiments.cohort import BacktestCohortBuilder, BacktestOutcomeRow
from app.modules.backtest_experiments.models import (
    BacktestExperimentCohort,
    BacktestExperimentRun,
    BacktestExperimentRunStatus,
)
from app.modules.backtest_experiments.repository import BacktestExperimentRepository
from app.modules.backtest_experiments.schemas import (
    BACKTEST_EXPERIMENT_VERSION,
    SUPPORTED_COHORT_DIMENSIONS,
    BacktestExperimentRunRequest,
)


class BacktestExperimentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = BacktestExperimentRepository(session)
        self.cohort_builder = BacktestCohortBuilder()

    async def run_experiment(self, payload: BacktestExperimentRunRequest) -> BacktestExperimentRun:
        effective_dimensions = self.effective_dimensions(payload.cohort_dimensions)
        run = await self.repository.create_run(
            BacktestExperimentRun(
                workspace_id=payload.workspace_id,
                name=payload.name,
                description=payload.description,
                status=BacktestExperimentRunStatus.PENDING,
                experiment_version=BACKTEST_EXPERIMENT_VERSION,
                filters_json=payload.filters.model_dump(mode="json"),
                cohort_dimensions_json=effective_dimensions,
                horizons_json=payload.horizons_minutes,
                minimum_sample_size=payload.minimum_sample_size,
                summary="Experiment is pending.",
            )
        )
        try:
            rows = await self.repository.list_outcome_rows(
                workspace_id=payload.workspace_id,
                horizons_minutes=payload.horizons_minutes,
                filters=payload.filters,
            )
            cohorts = self.cohort_builder.build_cohorts(
                workspace_id=payload.workspace_id,
                experiment_run_id=run.id,
                rows=rows,
                dimensions=effective_dimensions,
                minimum_sample_size=payload.minimum_sample_size,
            )
            await self.repository.create_cohorts(cohorts)
            run.signal_count = len({row.signal.id for row in rows})
            run.outcome_count = len(rows)
            run.cohort_count = len(cohorts)
            run.status = self.completed_status(rows, cohorts, payload.minimum_sample_size)
            run.summary = experiment_summary(
                signal_count=run.signal_count,
                outcome_count=run.outcome_count,
                cohort_count=run.cohort_count,
                skipped_dimensions=[
                    dimension
                    for dimension in payload.cohort_dimensions
                    if dimension not in effective_dimensions
                ],
            )
            await self.session.commit()
            await self.session.refresh(run)
            return run
        except Exception as error:
            run.status = BacktestExperimentRunStatus.FAILED
            run.error_message = str(error)
            run.summary = "Experiment failed before cohort analysis completed."
            await self.session.commit()
            await self.session.refresh(run)
            return run

    async def get_experiment_run(self, run_id: UUID) -> BacktestExperimentRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(
                404,
                "backtest_experiment_run_not_found",
                "Backtest experiment run not found",
            )
        return run

    async def list_experiment_runs(
        self,
        workspace_id: UUID,
        limit: int,
        status: str | None = None,
    ) -> list[BacktestExperimentRun]:
        return await self.repository.list_runs(workspace_id=workspace_id, limit=limit, status=status)

    async def list_experiment_cohorts(self, run_id: UUID) -> list[BacktestExperimentCohort]:
        await self.get_experiment_run(run_id)
        return await self.repository.list_cohorts(run_id)

    async def summarize_experiment(self, run_id: UUID) -> str:
        run = await self.get_experiment_run(run_id)
        return run.summary

    def effective_dimensions(self, dimensions: list[str]) -> list[str]:
        return [dimension for dimension in dimensions if dimension in SUPPORTED_COHORT_DIMENSIONS]

    def completed_status(
        self,
        rows: list[BacktestOutcomeRow],
        cohorts: list[BacktestExperimentCohort],
        minimum_sample_size: int,
    ) -> str:
        if not rows or not cohorts:
            return BacktestExperimentRunStatus.COMPLETED_WITH_WARNINGS
        low_sample_count = sum(1 for cohort in cohorts if cohort.sample_size < minimum_sample_size)
        if low_sample_count:
            return BacktestExperimentRunStatus.COMPLETED_WITH_WARNINGS
        return BacktestExperimentRunStatus.COMPLETED


def experiment_summary(
    signal_count: int,
    outcome_count: int,
    cohort_count: int,
    skipped_dimensions: list[str],
) -> str:
    if outcome_count == 0:
        base = "No existing signal outcomes matched the bounded experiment filters."
    else:
        base = (
            f"Analyzed {outcome_count} stored outcomes from {signal_count} signals "
            f"and created {cohort_count} historical behavior cohorts."
        )
    if skipped_dimensions:
        return f"{base} Skipped unavailable optional dimensions: {', '.join(skipped_dimensions)}."
    return base
