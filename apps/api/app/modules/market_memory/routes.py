from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.candles.timeframes import Timeframe
from app.modules.market_memory.models import (
    MarketMemoryDataQualityLabel,
    MarketMemoryFreshnessLabel,
)
from app.modules.market_memory.schemas import (
    MarketMemorySnapshotBuildRequest,
    MarketMemorySnapshotListFilters,
    MarketMemoryWorkspaceRefreshResponse,
    RollingMarketStateSnapshotRead,
)
from app.modules.market_memory.service import MarketMemoryService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/market-memory", tags=["market-memory"])


def get_market_memory_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> MarketMemoryService:
    return MarketMemoryService(session)


@router.post(
    "/snapshots",
    response_model=RollingMarketStateSnapshotRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def build_market_memory_snapshot(
    payload: MarketMemorySnapshotBuildRequest,
    service: Annotated[MarketMemoryService, Depends(get_market_memory_service)],
) -> RollingMarketStateSnapshotRead:
    snapshot = await service.build_state_snapshot(
        workspace_id=payload.workspace_id,
        symbol_id=payload.symbol_id,
        source_id=payload.source_id,
        timeframe=payload.timeframe.value,
        force_recompute=payload.force_recompute,
    )
    return RollingMarketStateSnapshotRead.model_validate(snapshot)


@router.get("/snapshots", response_model=list[RollingMarketStateSnapshotRead])
async def list_market_memory_snapshots(
    service: Annotated[MarketMemoryService, Depends(get_market_memory_service)],
    workspace_id: Annotated[UUID, Query(alias="workspaceId")],
    symbol_id: Annotated[UUID | None, Query(alias="symbolId")] = None,
    source_id: Annotated[UUID | None, Query(alias="sourceId")] = None,
    timeframe: Timeframe | None = None,
    freshness_label: Annotated[
        MarketMemoryFreshnessLabel | None,
        Query(alias="freshnessLabel"),
    ] = None,
    data_quality_label: Annotated[
        MarketMemoryDataQualityLabel | None,
        Query(alias="dataQualityLabel"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RollingMarketStateSnapshotRead]:
    snapshots = await service.list_state_snapshots(
        MarketMemorySnapshotListFilters(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            timeframe=timeframe,
            freshness_label=freshness_label,
            data_quality_label=data_quality_label,
            limit=limit,
            offset=offset,
        )
    )
    return [RollingMarketStateSnapshotRead.model_validate(snapshot) for snapshot in snapshots]


@router.get("/snapshots/by-symbol", response_model=RollingMarketStateSnapshotRead)
async def get_market_memory_snapshot_by_symbol(
    service: Annotated[MarketMemoryService, Depends(get_market_memory_service)],
    workspace_id: Annotated[UUID, Query(alias="workspaceId")],
    symbol_id: Annotated[UUID, Query(alias="symbolId")],
    timeframe: Timeframe,
    source_id: Annotated[UUID | None, Query(alias="sourceId")] = None,
) -> RollingMarketStateSnapshotRead:
    snapshot = await service.get_state_snapshot(
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        source_id=source_id,
        timeframe=timeframe.value,
    )
    return RollingMarketStateSnapshotRead.model_validate(snapshot)


@router.post(
    "/workspaces/{workspace_id}/refresh",
    response_model=MarketMemoryWorkspaceRefreshResponse,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def refresh_workspace_market_memory_snapshots(
    workspace_id: UUID,
    service: Annotated[MarketMemoryService, Depends(get_market_memory_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 500,
) -> MarketMemoryWorkspaceRefreshResponse:
    snapshots, skipped_count = await service.refresh_workspace_snapshots(
        workspace_id=workspace_id,
        limit=limit,
    )
    return MarketMemoryWorkspaceRefreshResponse(
        workspace_id=workspace_id,
        requested_limit=limit,
        refreshed_count=len(snapshots),
        skipped_count=skipped_count,
        snapshots=[
            RollingMarketStateSnapshotRead.model_validate(snapshot) for snapshot in snapshots
        ],
    )
