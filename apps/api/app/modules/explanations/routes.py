from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.explanations.schemas import DeterministicExplanationRead
from app.modules.explanations.service import DeterministicExplanationService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(tags=["deterministic-explanations"])


def get_deterministic_explanation_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> DeterministicExplanationService:
    return DeterministicExplanationService(session)


@router.post(
    "/signals/{signal_id}/deterministic-explanation",
    response_model=DeterministicExplanationRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def generate_signal_deterministic_explanation(
    signal_id: UUID,
    service: Annotated[
        DeterministicExplanationService,
        Depends(get_deterministic_explanation_service),
    ],
) -> DeterministicExplanationRead:
    return await service.generate_for_signal_id(signal_id)


@router.get(
    "/signals/{signal_id}/deterministic-explanation",
    response_model=DeterministicExplanationRead,
)
async def get_signal_deterministic_explanation(
    signal_id: UUID,
    service: Annotated[
        DeterministicExplanationService,
        Depends(get_deterministic_explanation_service),
    ],
) -> DeterministicExplanationRead:
    return await service.get_by_signal_id(signal_id)


@router.post(
    "/analysis-runs/{analysis_run_id}/deterministic-explanation",
    response_model=DeterministicExplanationRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def generate_analysis_run_deterministic_explanation(
    analysis_run_id: UUID,
    service: Annotated[
        DeterministicExplanationService,
        Depends(get_deterministic_explanation_service),
    ],
) -> DeterministicExplanationRead:
    return await service.generate_for_analysis_run_id(analysis_run_id)


@router.get(
    "/analysis-runs/{analysis_run_id}/deterministic-explanation",
    response_model=DeterministicExplanationRead,
)
async def get_analysis_run_deterministic_explanation(
    analysis_run_id: UUID,
    service: Annotated[
        DeterministicExplanationService,
        Depends(get_deterministic_explanation_service),
    ],
) -> DeterministicExplanationRead:
    return await service.get_by_analysis_run_id(analysis_run_id)
