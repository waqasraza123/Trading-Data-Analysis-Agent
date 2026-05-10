from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.scenario_ensembles.schemas import (
    ScenarioConsensusResultRead,
    ScenarioEnsembleItemRead,
    ScenarioEnsembleRequest,
    ScenarioEnsembleResponse,
    ScenarioEnsembleRunRead,
)
from app.modules.scenario_ensembles.service import ScenarioEnsembleService

router = APIRouter(tags=["scenario-ensembles"])


def get_scenario_ensemble_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ScenarioEnsembleService:
    return ScenarioEnsembleService(session)


@router.post(
    "/signals/{signal_id}/scenario-ensemble",
    response_model=ScenarioEnsembleResponse,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def run_signal_scenario_ensemble(
    signal_id: UUID,
    request: ScenarioEnsembleRequest,
    service: Annotated[
        ScenarioEnsembleService,
        Depends(get_scenario_ensemble_service),
    ],
) -> ScenarioEnsembleResponse:
    return await service.run_signal_ensemble(
        signal_id=signal_id,
        providers=request.providers,
        force_recompute=request.force_recompute,
    )


@router.get(
    "/signals/{signal_id}/scenario-ensembles",
    response_model=list[ScenarioEnsembleRunRead],
)
async def list_signal_scenario_ensembles(
    signal_id: UUID,
    service: Annotated[
        ScenarioEnsembleService,
        Depends(get_scenario_ensemble_service),
    ],
) -> list[ScenarioEnsembleRunRead]:
    return await service.list_signal_runs(signal_id)


@router.get(
    "/scenario-ensembles/{ensemble_run_id}",
    response_model=ScenarioEnsembleResponse,
)
async def get_scenario_ensemble(
    ensemble_run_id: UUID,
    service: Annotated[
        ScenarioEnsembleService,
        Depends(get_scenario_ensemble_service),
    ],
) -> ScenarioEnsembleResponse:
    return await service.get_run(ensemble_run_id)


@router.get(
    "/scenario-ensembles/{ensemble_run_id}/items",
    response_model=list[ScenarioEnsembleItemRead],
)
async def list_scenario_ensemble_items(
    ensemble_run_id: UUID,
    service: Annotated[
        ScenarioEnsembleService,
        Depends(get_scenario_ensemble_service),
    ],
) -> list[ScenarioEnsembleItemRead]:
    return await service.list_items(ensemble_run_id)


@router.get(
    "/scenario-ensembles/{ensemble_run_id}/consensus",
    response_model=list[ScenarioConsensusResultRead],
)
async def list_scenario_ensemble_consensus(
    ensemble_run_id: UUID,
    service: Annotated[
        ScenarioEnsembleService,
        Depends(get_scenario_ensemble_service),
    ],
) -> list[ScenarioConsensusResultRead]:
    return await service.list_consensus(ensemble_run_id)
