from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.market_scans.models import MarketWatchlistStatus, ScheduledScanConfigStatus
from app.modules.market_scans.scanner import MarketScanExecutor
from app.modules.market_scans.schemas import (
    RunDueScansRequest,
    RunDueScansResponse,
    ScheduledScanConfigCreate,
    ScheduledScanConfigRead,
    ScheduledScanConfigUpdate,
    ScheduledScanRunItemRead,
    ScheduledScanRunRead,
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemRead,
    WatchlistItemUpdate,
    WatchlistRead,
    WatchlistUpdate,
)
from app.modules.market_scans.service import MarketScanService

router = APIRouter(tags=["market-scans"])


def get_market_scan_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> MarketScanService:
    return MarketScanService(session)


def get_market_scan_executor(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> MarketScanExecutor:
    return MarketScanExecutor(session)


@router.post(
    "/market-watchlists",
    response_model=WatchlistRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_watchlist(
    payload: WatchlistCreate,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> WatchlistRead:
    watchlist = await service.create_watchlist(payload)
    return WatchlistRead.model_validate(watchlist)


@router.get("/market-watchlists", response_model=list[WatchlistRead])
async def list_watchlists(
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
    workspace_id: UUID,
    status_filter: Annotated[MarketWatchlistStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[WatchlistRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    watchlists = await service.list_watchlists(
        workspace_id=workspace_id,
        status=status_filter,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [WatchlistRead.model_validate(watchlist) for watchlist in watchlists]


@router.get("/market-watchlists/{watchlist_id}", response_model=WatchlistRead)
async def get_watchlist(
    watchlist_id: UUID,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> WatchlistRead:
    watchlist = await service.get_watchlist(watchlist_id)
    return WatchlistRead.model_validate(watchlist)


@router.patch("/market-watchlists/{watchlist_id}", response_model=WatchlistRead)
async def update_watchlist(
    watchlist_id: UUID,
    payload: WatchlistUpdate,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> WatchlistRead:
    watchlist = await service.update_watchlist(watchlist_id, payload)
    return WatchlistRead.model_validate(watchlist)


@router.post(
    "/market-watchlists/{watchlist_id}/items",
    response_model=WatchlistItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_watchlist_item(
    watchlist_id: UUID,
    payload: WatchlistItemCreate,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> WatchlistItemRead:
    item = await service.add_watchlist_item(watchlist_id, payload)
    return WatchlistItemRead.model_validate(item)


@router.get("/market-watchlists/{watchlist_id}/items", response_model=list[WatchlistItemRead])
async def list_watchlist_items(
    watchlist_id: UUID,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
    is_active: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[WatchlistItemRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    items = await service.list_watchlist_items(
        watchlist_id=watchlist_id,
        is_active=is_active,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [WatchlistItemRead.model_validate(item) for item in items]


@router.patch("/market-watchlist-items/{item_id}", response_model=WatchlistItemRead)
async def update_watchlist_item(
    item_id: UUID,
    payload: WatchlistItemUpdate,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> WatchlistItemRead:
    item = await service.update_watchlist_item(item_id, payload)
    return WatchlistItemRead.model_validate(item)


@router.delete("/market-watchlist-items/{item_id}", response_model=WatchlistItemRead)
async def delete_watchlist_item(
    item_id: UUID,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> WatchlistItemRead:
    item = await service.remove_or_deactivate_watchlist_item(item_id)
    return WatchlistItemRead.model_validate(item)


@router.post(
    "/scheduled-scan-configs",
    response_model=ScheduledScanConfigRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_scan_config(
    payload: ScheduledScanConfigCreate,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> ScheduledScanConfigRead:
    config = await service.create_scan_config(payload)
    return ScheduledScanConfigRead.model_validate(config)


@router.get("/scheduled-scan-configs/due", response_model=list[ScheduledScanConfigRead])
async def list_due_scan_configs(
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
    workspace_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[ScheduledScanConfigRead]:
    configs = await service.list_due_scan_configs(workspace_id=workspace_id, limit=limit)
    return [ScheduledScanConfigRead.model_validate(config) for config in configs]


@router.post("/scheduled-scan-configs/run-due", response_model=RunDueScansResponse)
async def run_due_scan_configs(
    payload: RunDueScansRequest,
    executor: Annotated[MarketScanExecutor, Depends(get_market_scan_executor)],
) -> RunDueScansResponse:
    runs = await executor.run_due_scan_configs(
        workspace_id=payload.workspace_id,
        limit=payload.limit,
    )
    return RunDueScansResponse(
        run_count=len(runs),
        runs=[ScheduledScanRunRead.model_validate(run) for run in runs],
    )


@router.get("/scheduled-scan-configs", response_model=list[ScheduledScanConfigRead])
async def list_scan_configs(
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
    workspace_id: UUID,
    status_filter: Annotated[ScheduledScanConfigStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ScheduledScanConfigRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    configs = await service.list_scan_configs(
        workspace_id=workspace_id,
        status=status_filter,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [ScheduledScanConfigRead.model_validate(config) for config in configs]


@router.get("/scheduled-scan-configs/{scan_config_id}", response_model=ScheduledScanConfigRead)
async def get_scan_config(
    scan_config_id: UUID,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> ScheduledScanConfigRead:
    config = await service.get_scan_config(scan_config_id)
    return ScheduledScanConfigRead.model_validate(config)


@router.patch("/scheduled-scan-configs/{scan_config_id}", response_model=ScheduledScanConfigRead)
async def update_scan_config(
    scan_config_id: UUID,
    payload: ScheduledScanConfigUpdate,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> ScheduledScanConfigRead:
    config = await service.update_scan_config(scan_config_id, payload)
    return ScheduledScanConfigRead.model_validate(config)


@router.post(
    "/scheduled-scan-configs/{scan_config_id}/pause",
    response_model=ScheduledScanConfigRead,
)
async def pause_scan_config(
    scan_config_id: UUID,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> ScheduledScanConfigRead:
    config = await service.pause_scan_config(scan_config_id)
    return ScheduledScanConfigRead.model_validate(config)


@router.post(
    "/scheduled-scan-configs/{scan_config_id}/resume",
    response_model=ScheduledScanConfigRead,
)
async def resume_scan_config(
    scan_config_id: UUID,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> ScheduledScanConfigRead:
    config = await service.resume_scan_config(scan_config_id)
    return ScheduledScanConfigRead.model_validate(config)


@router.post(
    "/scheduled-scan-configs/{scan_config_id}/archive",
    response_model=ScheduledScanConfigRead,
)
async def archive_scan_config(
    scan_config_id: UUID,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> ScheduledScanConfigRead:
    config = await service.archive_scan_config(scan_config_id)
    return ScheduledScanConfigRead.model_validate(config)


@router.post("/scheduled-scan-configs/{scan_config_id}/run", response_model=ScheduledScanRunRead)
async def run_scan_config(
    scan_config_id: UUID,
    executor: Annotated[MarketScanExecutor, Depends(get_market_scan_executor)],
) -> ScheduledScanRunRead:
    run = await executor.run_scan_config(scan_config_id, force=True)
    return ScheduledScanRunRead.model_validate(run)


@router.get("/scheduled-scan-runs/{scan_run_id}", response_model=ScheduledScanRunRead)
async def get_scan_run(
    scan_run_id: UUID,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
) -> ScheduledScanRunRead:
    run = await service.get_scan_run(scan_run_id)
    return ScheduledScanRunRead.model_validate(run)


@router.get(
    "/scheduled-scan-runs/{scan_run_id}/items",
    response_model=list[ScheduledScanRunItemRead],
)
async def list_scan_run_items(
    scan_run_id: UUID,
    service: Annotated[MarketScanService, Depends(get_market_scan_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ScheduledScanRunItemRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    items = await service.list_scan_run_items(
        scan_run_id=scan_run_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [ScheduledScanRunItemRead.model_validate(item) for item in items]
