from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.cross_asset_context.schemas import (
    CrossAssetContextBuildRequest,
    CrossAssetContextResultRead,
    CrossAssetContextRunRead,
)
from app.modules.cross_asset_context.service import CrossAssetContextService

router = APIRouter(tags=["cross-asset-context"])


def get_cross_asset_context_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> CrossAssetContextService:
    return CrossAssetContextService(session)


@router.post(
    "/analysis-runs/{analysis_run_id}/cross-asset-context",
    response_model=CrossAssetContextRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def build_analysis_run_cross_asset_context(
    analysis_run_id: UUID,
    payload: CrossAssetContextBuildRequest,
    service: Annotated[CrossAssetContextService, Depends(get_cross_asset_context_service)],
) -> CrossAssetContextRunRead:
    run = await service.build_for_analysis_run(
        analysis_run_id=analysis_run_id,
        compared_symbol_ids=payload.compared_symbol_ids,
        force_recompute=payload.force_recompute,
    )
    return CrossAssetContextRunRead.model_validate(run)


@router.get(
    "/analysis-runs/{analysis_run_id}/cross-asset-context",
    response_model=CrossAssetContextRunRead,
)
async def get_analysis_run_cross_asset_context(
    analysis_run_id: UUID,
    service: Annotated[CrossAssetContextService, Depends(get_cross_asset_context_service)],
) -> CrossAssetContextRunRead:
    run = await service.get_for_analysis_run(analysis_run_id)
    return CrossAssetContextRunRead.model_validate(run)


@router.post(
    "/signals/{signal_id}/cross-asset-context",
    response_model=CrossAssetContextRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def build_signal_cross_asset_context(
    signal_id: UUID,
    payload: CrossAssetContextBuildRequest,
    service: Annotated[CrossAssetContextService, Depends(get_cross_asset_context_service)],
) -> CrossAssetContextRunRead:
    run = await service.build_for_signal(
        signal_id=signal_id,
        compared_symbol_ids=payload.compared_symbol_ids,
        force_recompute=payload.force_recompute,
    )
    return CrossAssetContextRunRead.model_validate(run)


@router.get("/signals/{signal_id}/cross-asset-context", response_model=CrossAssetContextRunRead)
async def get_signal_cross_asset_context(
    signal_id: UUID,
    service: Annotated[CrossAssetContextService, Depends(get_cross_asset_context_service)],
) -> CrossAssetContextRunRead:
    run = await service.get_for_signal(signal_id)
    return CrossAssetContextRunRead.model_validate(run)


@router.get(
    "/cross-asset-context/runs/{run_id}/results",
    response_model=list[CrossAssetContextResultRead],
)
async def list_cross_asset_context_results(
    run_id: UUID,
    service: Annotated[CrossAssetContextService, Depends(get_cross_asset_context_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CrossAssetContextResultRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    results = await service.list_results(
        context_run_id=run_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [CrossAssetContextResultRead.model_validate(result) for result in results]
