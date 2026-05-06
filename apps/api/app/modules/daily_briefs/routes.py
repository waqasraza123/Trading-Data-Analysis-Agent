from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.daily_briefs.models import (
    DailyBriefItemType,
    DailyBriefPriority,
    DailyBriefStatus,
    DailyBriefType,
)
from app.modules.daily_briefs.schemas import (
    DailyBriefCreate,
    DailyBriefDailyCreate,
    DailyBriefItemRead,
    DailyBriefRunListFilters,
    DailyBriefRunRead,
    DailyBriefSessionCreate,
    DailyBriefWatchlistCreate,
)
from app.modules.daily_briefs.service import DailyBriefService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(tags=["daily-briefs"])


def get_daily_brief_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> DailyBriefService:
    return DailyBriefService(session)


@router.post(
    "/daily-briefs",
    response_model=DailyBriefRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def create_daily_brief(
    payload: DailyBriefCreate,
    service: Annotated[DailyBriefService, Depends(get_daily_brief_service)],
) -> DailyBriefRunRead:
    run = await service.create_brief(payload)
    return DailyBriefRunRead.model_validate(run)


@router.post(
    "/daily-briefs/daily",
    response_model=DailyBriefRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def create_daily_directional_brief(
    payload: DailyBriefDailyCreate,
    service: Annotated[DailyBriefService, Depends(get_daily_brief_service)],
) -> DailyBriefRunRead:
    run = await service.create_daily_brief(
        workspace_id=payload.workspace_id,
        brief_date=payload.date,
        timezone=payload.timezone,
        filters=payload.filters,
    )
    return DailyBriefRunRead.model_validate(run)


@router.post(
    "/daily-briefs/session",
    response_model=DailyBriefRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def create_session_directional_brief(
    payload: DailyBriefSessionCreate,
    service: Annotated[DailyBriefService, Depends(get_daily_brief_service)],
) -> DailyBriefRunRead:
    run = await service.create_session_brief(
        workspace_id=payload.workspace_id,
        session_label=payload.session_label.value,
        brief_date=payload.date,
        timezone=payload.timezone,
        filters=payload.filters,
    )
    return DailyBriefRunRead.model_validate(run)


@router.post(
    "/daily-briefs/watchlist",
    response_model=DailyBriefRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def create_watchlist_directional_brief(
    payload: DailyBriefWatchlistCreate,
    service: Annotated[DailyBriefService, Depends(get_daily_brief_service)],
) -> DailyBriefRunRead:
    run = await service.create_watchlist_brief(
        workspace_id=payload.workspace_id,
        watchlist_id=payload.watchlist_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        timezone=payload.timezone,
        filters=payload.filters,
    )
    return DailyBriefRunRead.model_validate(run)


@router.get("/daily-briefs", response_model=list[DailyBriefRunRead])
async def list_daily_briefs(
    service: Annotated[DailyBriefService, Depends(get_daily_brief_service)],
    workspace_id: Annotated[UUID, Query(alias="workspaceId")],
    brief_type: Annotated[DailyBriefType | None, Query(alias="briefType")] = None,
    status_filter: Annotated[DailyBriefStatus | None, Query(alias="status")] = None,
    watchlist_id: Annotated[UUID | None, Query(alias="watchlistId")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DailyBriefRunRead]:
    runs = await service.list_briefs(
        DailyBriefRunListFilters(
            workspace_id=workspace_id,
            brief_type=brief_type,
            status=status_filter,
            watchlist_id=watchlist_id,
            limit=limit,
            offset=offset,
        )
    )
    return [DailyBriefRunRead.model_validate(run) for run in runs]


@router.get("/daily-briefs/{brief_id}", response_model=DailyBriefRunRead)
async def get_daily_brief(
    brief_id: UUID,
    service: Annotated[DailyBriefService, Depends(get_daily_brief_service)],
) -> DailyBriefRunRead:
    run = await service.get_brief(brief_id)
    return DailyBriefRunRead.model_validate(run)


@router.get("/daily-briefs/{brief_id}/items", response_model=list[DailyBriefItemRead])
async def list_daily_brief_items(
    brief_id: UUID,
    service: Annotated[DailyBriefService, Depends(get_daily_brief_service)],
    item_type: Annotated[DailyBriefItemType | None, Query(alias="itemType")] = None,
    priority: Annotated[DailyBriefPriority | None, Query(alias="priority")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 150,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DailyBriefItemRead]:
    items = await service.list_brief_items(
        brief_id=brief_id,
        item_type=item_type.value if item_type is not None else None,
        priority=priority.value if priority is not None else None,
        limit=limit,
        offset=offset,
    )
    return [DailyBriefItemRead.model_validate(item) for item in items]


@router.get("/workspaces/{workspace_id}/daily-brief/latest", response_model=DailyBriefRunRead)
async def get_latest_workspace_daily_brief(
    workspace_id: UUID,
    service: Annotated[DailyBriefService, Depends(get_daily_brief_service)],
    brief_type: Annotated[DailyBriefType | None, Query(alias="briefType")] = DailyBriefType.DAILY,
    watchlist_id: Annotated[UUID | None, Query(alias="watchlistId")] = None,
) -> DailyBriefRunRead:
    run = await service.get_latest_brief(
        workspace_id=workspace_id,
        brief_type=brief_type,
        watchlist_id=watchlist_id,
    )
    return DailyBriefRunRead.model_validate(run)
