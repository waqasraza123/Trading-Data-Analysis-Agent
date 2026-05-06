from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.workspace_overview.schemas import WorkspaceOverviewQuery, WorkspaceOverviewResponse
from app.modules.workspace_overview.service import WorkspaceOverviewService

router = APIRouter(prefix="/workspaces", tags=["workspace-overview"])


def get_workspace_overview_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> WorkspaceOverviewService:
    return WorkspaceOverviewService(session=session, settings=request.app.state.settings)


@router.get(
    "/{workspace_id}/overview",
    response_model=WorkspaceOverviewResponse,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_READ))],
)
async def get_workspace_overview(
    workspace_id: UUID,
    service: Annotated[WorkspaceOverviewService, Depends(get_workspace_overview_service)],
    period_start: Annotated[datetime | None, Query(alias="periodStart")] = None,
    period_end: Annotated[datetime | None, Query(alias="periodEnd")] = None,
    watchlist_id: Annotated[UUID | None, Query(alias="watchlistId")] = None,
    preference_profile_id: Annotated[UUID | None, Query(alias="preferenceProfileId")] = None,
    include_read_models: Annotated[bool, Query(alias="includeReadModels")] = True,
    include_notifications: Annotated[bool, Query(alias="includeNotifications")] = True,
    include_journal: Annotated[bool, Query(alias="includeJournal")] = True,
    include_quality: Annotated[bool, Query(alias="includeQuality")] = True,
) -> WorkspaceOverviewResponse:
    return await service.build_overview(
        workspace_id,
        WorkspaceOverviewQuery(
            period_start=period_start,
            period_end=period_end,
            watchlist_id=watchlist_id,
            preference_profile_id=preference_profile_id,
            include_read_models=include_read_models,
            include_notifications=include_notifications,
            include_journal=include_journal,
            include_quality=include_quality,
        ),
    )
