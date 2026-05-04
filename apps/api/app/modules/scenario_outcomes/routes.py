from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.scenario_outcomes.schemas import (
    ReasoningRunScenarioOutcomesRead,
    ReasoningRunScenarioOutcomesRequest,
    ScenarioHypothesisOutcomeRead,
    ScenarioHypothesisOutcomeRequest,
    ScenarioOutcomeSummaryRequest,
    ScenarioOutcomeSummaryRunRead,
)
from app.modules.scenario_outcomes.service import ScenarioOutcomeService

router = APIRouter(tags=["scenario-outcomes"])


def get_scenario_outcome_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ScenarioOutcomeService:
    return ScenarioOutcomeService(session)


@router.post(
    "/reasoning/scenarios/{scenario_hypothesis_id}/outcome",
    response_model=ScenarioHypothesisOutcomeRead,
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_scenario_hypothesis_outcome(
    scenario_hypothesis_id: UUID,
    payload: ScenarioHypothesisOutcomeRequest,
    service: Annotated[ScenarioOutcomeService, Depends(get_scenario_outcome_service)],
) -> ScenarioHypothesisOutcomeRead:
    return await service.evaluate_scenario_hypothesis(
        scenario_hypothesis_id=scenario_hypothesis_id,
        horizon_minutes=payload.horizon_minutes,
        force_recompute=payload.force_recompute,
    )


@router.post(
    "/reasoning/runs/{reasoning_run_id}/scenario-outcomes",
    response_model=ReasoningRunScenarioOutcomesRead,
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_reasoning_run_scenario_outcomes(
    reasoning_run_id: UUID,
    payload: ReasoningRunScenarioOutcomesRequest,
    service: Annotated[ScenarioOutcomeService, Depends(get_scenario_outcome_service)],
) -> ReasoningRunScenarioOutcomesRead:
    return await service.evaluate_reasoning_run(
        reasoning_run_id=reasoning_run_id,
        horizons_minutes=payload.horizons_minutes,
        force_recompute=payload.force_recompute,
    )


@router.get(
    "/reasoning/runs/{reasoning_run_id}/scenario-outcomes",
    response_model=ReasoningRunScenarioOutcomesRead,
)
async def get_reasoning_run_scenario_outcomes(
    reasoning_run_id: UUID,
    service: Annotated[ScenarioOutcomeService, Depends(get_scenario_outcome_service)],
) -> ReasoningRunScenarioOutcomesRead:
    return await service.get_hypothesis_outcomes(reasoning_run_id)


@router.post(
    "/scenario-outcomes/summary",
    response_model=ScenarioOutcomeSummaryRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def summarize_scenario_outcomes(
    payload: ScenarioOutcomeSummaryRequest,
    service: Annotated[ScenarioOutcomeService, Depends(get_scenario_outcome_service)],
) -> ScenarioOutcomeSummaryRunRead:
    return await service.summarize_scenario_outcomes(payload)


@router.get(
    "/scenario-outcomes/summary/{summary_run_id}",
    response_model=ScenarioOutcomeSummaryRunRead,
)
async def get_scenario_outcome_summary(
    summary_run_id: UUID,
    service: Annotated[ScenarioOutcomeService, Depends(get_scenario_outcome_service)],
) -> ScenarioOutcomeSummaryRunRead:
    return await service.get_summary_run(summary_run_id)
