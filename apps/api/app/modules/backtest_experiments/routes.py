from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.backtest_experiments.schemas import (
    BacktestExperimentCohortRead,
    BacktestExperimentRunRead,
    BacktestExperimentRunRequest,
)
from app.modules.backtest_experiments.service import BacktestExperimentService

router = APIRouter(tags=["backtest-experiments"])


def get_backtest_experiment_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> BacktestExperimentService:
    return BacktestExperimentService(session)


@router.post(
    "/backtest-experiments/run",
    response_model=BacktestExperimentRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def run_backtest_experiment(
    payload: BacktestExperimentRunRequest,
    service: Annotated[BacktestExperimentService, Depends(get_backtest_experiment_service)],
) -> BacktestExperimentRunRead:
    run = await service.run_experiment(payload)
    return BacktestExperimentRunRead.model_validate(run)


@router.get("/backtest-experiments/runs", response_model=list[BacktestExperimentRunRead])
async def list_backtest_experiment_runs(
    service: Annotated[BacktestExperimentService, Depends(get_backtest_experiment_service)],
    workspace_id: UUID,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    status: str | None = None,
) -> list[BacktestExperimentRunRead]:
    runs = await service.list_experiment_runs(
        workspace_id=workspace_id,
        limit=limit,
        status=status,
    )
    return [BacktestExperimentRunRead.model_validate(run) for run in runs]


@router.get("/backtest-experiments/runs/{run_id}", response_model=BacktestExperimentRunRead)
async def get_backtest_experiment_run(
    run_id: UUID,
    service: Annotated[BacktestExperimentService, Depends(get_backtest_experiment_service)],
) -> BacktestExperimentRunRead:
    run = await service.get_experiment_run(run_id)
    return BacktestExperimentRunRead.model_validate(run)


@router.get(
    "/backtest-experiments/runs/{run_id}/cohorts",
    response_model=list[BacktestExperimentCohortRead],
)
async def list_backtest_experiment_cohorts(
    run_id: UUID,
    service: Annotated[BacktestExperimentService, Depends(get_backtest_experiment_service)],
) -> list[BacktestExperimentCohortRead]:
    cohorts = await service.list_experiment_cohorts(run_id)
    return [BacktestExperimentCohortRead.model_validate(cohort) for cohort in cohorts]
