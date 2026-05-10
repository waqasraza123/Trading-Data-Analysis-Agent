from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.market_regimes.schemas import (
    MarketRegimeContextRead,
    MarketRegimeGenerationRequest,
)
from app.modules.market_regimes.service import MarketRegimeContextService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(tags=["market-regimes"])


def get_market_regime_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> MarketRegimeContextService:
    return MarketRegimeContextService(session)


@router.post(
    "/analysis-runs/{analysis_run_id}/market-regime",
    response_model=MarketRegimeContextRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def generate_analysis_run_market_regime(
    analysis_run_id: UUID,
    service: Annotated[MarketRegimeContextService, Depends(get_market_regime_service)],
    payload: MarketRegimeGenerationRequest | None = None,
) -> MarketRegimeContextRead:
    request = payload or MarketRegimeGenerationRequest()
    context = await service.generate_for_analysis_run(
        analysis_run_id=analysis_run_id,
        force_recompute=request.force_recompute,
    )
    return MarketRegimeContextRead.model_validate(context)


@router.get(
    "/analysis-runs/{analysis_run_id}/market-regime",
    response_model=MarketRegimeContextRead,
)
async def get_analysis_run_market_regime(
    analysis_run_id: UUID,
    service: Annotated[MarketRegimeContextService, Depends(get_market_regime_service)],
) -> MarketRegimeContextRead:
    context = await service.get_for_analysis_run(analysis_run_id)
    return MarketRegimeContextRead.model_validate(context)


@router.post(
    "/signals/{signal_id}/market-regime",
    response_model=MarketRegimeContextRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def generate_signal_market_regime(
    signal_id: UUID,
    service: Annotated[MarketRegimeContextService, Depends(get_market_regime_service)],
    payload: MarketRegimeGenerationRequest | None = None,
) -> MarketRegimeContextRead:
    request = payload or MarketRegimeGenerationRequest()
    context = await service.generate_for_signal(
        signal_id=signal_id,
        force_recompute=request.force_recompute,
    )
    return MarketRegimeContextRead.model_validate(context)


@router.get("/signals/{signal_id}/market-regime", response_model=MarketRegimeContextRead)
async def get_signal_market_regime(
    signal_id: UUID,
    service: Annotated[MarketRegimeContextService, Depends(get_market_regime_service)],
) -> MarketRegimeContextRead:
    context = await service.get_for_signal(signal_id)
    return MarketRegimeContextRead.model_validate(context)
