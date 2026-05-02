from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.profile_simulations.schemas import (
    ProfileSimulationRunRequest,
    StrategyProfileSimulationResultRead,
    StrategyProfileSimulationRunRead,
)
from app.modules.profile_simulations.service import ProfileSimulationService

router = APIRouter(prefix="/profile-simulations", tags=["profile-simulations"])


def get_profile_simulation_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ProfileSimulationService:
    return ProfileSimulationService(session)


@router.post("/run", response_model=StrategyProfileSimulationRunRead)
async def run_profile_simulation(
    request: ProfileSimulationRunRequest,
    service: Annotated[ProfileSimulationService, Depends(get_profile_simulation_service)],
) -> StrategyProfileSimulationRunRead:
    run = await service.run_simulation(request)
    return StrategyProfileSimulationRunRead.model_validate(run)


@router.get("/runs/{run_id}", response_model=StrategyProfileSimulationRunRead)
async def get_profile_simulation_run(
    run_id: UUID,
    service: Annotated[ProfileSimulationService, Depends(get_profile_simulation_service)],
) -> StrategyProfileSimulationRunRead:
    run = await service.get_simulation_run(run_id)
    return StrategyProfileSimulationRunRead.model_validate(run)


@router.get("/runs/{run_id}/results", response_model=list[StrategyProfileSimulationResultRead])
async def list_profile_simulation_results(
    run_id: UUID,
    service: Annotated[ProfileSimulationService, Depends(get_profile_simulation_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[StrategyProfileSimulationResultRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    results = await service.list_simulation_results(
        run_id=run_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [StrategyProfileSimulationResultRead.model_validate(result) for result in results]
