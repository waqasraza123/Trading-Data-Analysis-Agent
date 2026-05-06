from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.workspace_actions.schemas import (
    WorkspaceQuickActionRequest,
    WorkspaceQuickActionResponse,
)
from app.modules.workspace_actions.service import WorkspaceQuickActionService

router = APIRouter(prefix="/workspaces", tags=["workspace-actions"])


def get_workspace_quick_action_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> WorkspaceQuickActionService:
    return WorkspaceQuickActionService(session=session, settings=request.app.state.settings)


@router.post(
    "/{workspace_id}/quick-actions",
    response_model=WorkspaceQuickActionResponse,
    dependencies=[Depends(require_permission(Permission.SCANS_WRITE))],
)
async def run_workspace_quick_action(
    workspace_id: UUID,
    payload: WorkspaceQuickActionRequest,
    service: Annotated[WorkspaceQuickActionService, Depends(get_workspace_quick_action_service)],
) -> WorkspaceQuickActionResponse:
    return await service.run_action(workspace_id=workspace_id, payload=payload)
