from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.workspaces.schemas import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate
from app.modules.workspaces.service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def get_workspace_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> WorkspaceService:
    return WorkspaceService(session)


@router.post(
    "",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_ADMIN))],
)
async def create_workspace(
    payload: WorkspaceCreate,
    service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceRead:
    workspace = await service.create_workspace(payload)
    return WorkspaceRead.model_validate(workspace)


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[WorkspaceRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    workspaces = await service.list_workspaces(
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [WorkspaceRead.model_validate(workspace) for workspace in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    workspace_id: UUID,
    service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceRead:
    workspace = await service.get_workspace(workspace_id)
    return WorkspaceRead.model_validate(workspace)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_WRITE))],
)
async def update_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdate,
    service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceRead:
    workspace = await service.update_workspace(workspace_id, payload)
    return WorkspaceRead.model_validate(workspace)
