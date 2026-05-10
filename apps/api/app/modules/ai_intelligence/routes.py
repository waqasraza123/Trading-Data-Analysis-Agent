from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.ai_intelligence.schemas import (
    AiIntelligenceRequest,
    AiIntelligenceResponse,
    AiIntelligenceRunRead,
)
from app.modules.ai_intelligence.service import AiIntelligenceService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/ai-intelligence", tags=["ai-intelligence"])


def get_ai_intelligence_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> AiIntelligenceService:
    return AiIntelligenceService(session)


@router.post(
    "/signals/{signal_id}/analyze",
    response_model=AiIntelligenceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def generate_signal_ai_intelligence(
    signal_id: UUID,
    payload: AiIntelligenceRequest,
    service: Annotated[AiIntelligenceService, Depends(get_ai_intelligence_service)],
) -> AiIntelligenceResponse:
    return await service.generate_signal_intelligence(
        signal_id=signal_id,
        provider=payload.provider,
        model=payload.model,
        force_recompute=payload.force_recompute,
    )


@router.get("/runs/{run_id}", response_model=AiIntelligenceResponse)
async def get_ai_intelligence_run(
    run_id: UUID,
    service: Annotated[AiIntelligenceService, Depends(get_ai_intelligence_service)],
) -> AiIntelligenceResponse:
    return await service.get_run(run_id)


@router.get("/signals/{signal_id}/runs", response_model=list[AiIntelligenceRunRead])
async def list_signal_ai_intelligence_runs(
    signal_id: UUID,
    service: Annotated[AiIntelligenceService, Depends(get_ai_intelligence_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AiIntelligenceRunRead]:
    return await service.list_signal_runs(signal_id, limit=limit, offset=offset)
