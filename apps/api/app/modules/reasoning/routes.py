from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.reasoning.schemas import (
    ReasoningRunRead,
    ScenarioReasoningRequest,
    ScenarioReasoningResponse,
)
from app.modules.reasoning.service import ScenarioReasoningService

router = APIRouter(tags=["reasoning"])


def get_scenario_reasoning_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ScenarioReasoningService:
    return ScenarioReasoningService(session)


@router.post(
    "/signals/{signal_id}/reasoning/scenarios",
    response_model=ScenarioReasoningResponse,
)
async def generate_signal_reasoning_scenarios(
    signal_id: UUID,
    payload: ScenarioReasoningRequest,
    service: Annotated[ScenarioReasoningService, Depends(get_scenario_reasoning_service)],
) -> ScenarioReasoningResponse:
    return await service.generate_signal_scenarios(
        signal_id=signal_id,
        provider=payload.provider,
        model=payload.model,
        force_recompute=payload.force_recompute,
    )


@router.get("/signals/{signal_id}/reasoning/runs", response_model=list[ReasoningRunRead])
async def list_signal_reasoning_runs(
    signal_id: UUID,
    service: Annotated[ScenarioReasoningService, Depends(get_scenario_reasoning_service)],
) -> list[ReasoningRunRead]:
    return await service.get_signal_reasoning_runs(signal_id)


@router.get(
    "/signals/{signal_id}/reasoning/scenarios/latest",
    response_model=ScenarioReasoningResponse,
)
async def get_signal_latest_reasoning_scenarios(
    signal_id: UUID,
    service: Annotated[ScenarioReasoningService, Depends(get_scenario_reasoning_service)],
) -> ScenarioReasoningResponse:
    return await service.get_signal_latest_scenarios(signal_id)


@router.get("/reasoning/runs/{reasoning_run_id}", response_model=ScenarioReasoningResponse)
async def get_reasoning_run(
    reasoning_run_id: UUID,
    service: Annotated[ScenarioReasoningService, Depends(get_scenario_reasoning_service)],
) -> ScenarioReasoningResponse:
    return await service.get_reasoning_run(reasoning_run_id)
