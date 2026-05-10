from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.market_sessions.schemas import MarketSessionContextRead
from app.modules.market_sessions.service import MarketSessionService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(tags=["market-sessions"])


def get_market_session_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> MarketSessionService:
    return MarketSessionService(session)


@router.post(
    "/analysis-runs/{analysis_run_id}/market-session",
    response_model=MarketSessionContextRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def create_analysis_run_market_session(
    analysis_run_id: UUID,
    service: Annotated[MarketSessionService, Depends(get_market_session_service)],
) -> MarketSessionContextRead:
    return MarketSessionContextRead.model_validate(
        await service.create_for_analysis_run(analysis_run_id)
    )


@router.get(
    "/analysis-runs/{analysis_run_id}/market-session", response_model=MarketSessionContextRead
)
async def get_analysis_run_market_session(
    analysis_run_id: UUID,
    service: Annotated[MarketSessionService, Depends(get_market_session_service)],
) -> MarketSessionContextRead:
    return MarketSessionContextRead.model_validate(
        await service.get_for_analysis_run(analysis_run_id)
    )


@router.post(
    "/signals/{signal_id}/market-session",
    response_model=MarketSessionContextRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def create_signal_market_session(
    signal_id: UUID,
    service: Annotated[MarketSessionService, Depends(get_market_session_service)],
) -> MarketSessionContextRead:
    return MarketSessionContextRead.model_validate(await service.create_for_signal(signal_id))


@router.get("/signals/{signal_id}/market-session", response_model=MarketSessionContextRead)
async def get_signal_market_session(
    signal_id: UUID,
    service: Annotated[MarketSessionService, Depends(get_market_session_service)],
) -> MarketSessionContextRead:
    return MarketSessionContextRead.model_validate(await service.get_for_signal(signal_id))
