from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.llm_explanations.schemas import LlmExplanationRead
from app.modules.llm_explanations.service import LlmExplanationService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(tags=["llm-explanations"])


def get_llm_explanation_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> LlmExplanationService:
    return LlmExplanationService(session)


@router.post(
    "/signals/{signal_id}/llm-explanation",
    response_model=LlmExplanationRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def generate_signal_llm_explanation(
    signal_id: UUID,
    service: Annotated[LlmExplanationService, Depends(get_llm_explanation_service)],
) -> LlmExplanationRead:
    return await service.generate_for_signal(signal_id)


@router.get("/signals/{signal_id}/llm-explanation", response_model=LlmExplanationRead)
async def get_signal_llm_explanation(
    signal_id: UUID,
    service: Annotated[LlmExplanationService, Depends(get_llm_explanation_service)],
) -> LlmExplanationRead:
    return await service.get_for_signal(signal_id)


@router.post(
    "/analysis-runs/{analysis_run_id}/llm-explanation",
    response_model=LlmExplanationRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def generate_analysis_run_llm_explanation(
    analysis_run_id: UUID,
    service: Annotated[LlmExplanationService, Depends(get_llm_explanation_service)],
) -> LlmExplanationRead:
    return await service.generate_for_analysis_run_id(analysis_run_id)


@router.get(
    "/analysis-runs/{analysis_run_id}/llm-explanation",
    response_model=LlmExplanationRead,
)
async def get_analysis_run_llm_explanation(
    analysis_run_id: UUID,
    service: Annotated[LlmExplanationService, Depends(get_llm_explanation_service)],
) -> LlmExplanationRead:
    return await service.get_for_analysis_run_id(analysis_run_id)
