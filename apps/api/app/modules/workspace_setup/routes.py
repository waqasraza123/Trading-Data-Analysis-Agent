from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.workspace_setup.schemas import (
    WorkspaceSetupDemoWorkspaceRequest,
    WorkspaceSetupDemoWorkspaceResponse,
    WorkspaceSetupRunRead,
    WorkspaceSetupStartRequest,
    WorkspaceSetupStepRequest,
)
from app.modules.workspace_setup.service import WorkspaceSetupService
from app.modules.workspace_setup.steps import WorkspaceSetupStepKey

router = APIRouter(prefix="/workspace-setup", tags=["workspace-setup"])


def get_workspace_setup_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> WorkspaceSetupService:
    return WorkspaceSetupService(session=session, settings=request.app.state.settings)


@router.post(
    "/start",
    response_model=WorkspaceSetupRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_ADMIN))],
)
async def start_workspace_setup(
    payload: WorkspaceSetupStartRequest,
    service: Annotated[WorkspaceSetupService, Depends(get_workspace_setup_service)],
) -> WorkspaceSetupRunRead:
    return await service.start_setup(payload)


@router.get("/runs/{setup_run_id}", response_model=WorkspaceSetupRunRead)
async def get_workspace_setup_run(
    setup_run_id: UUID,
    service: Annotated[WorkspaceSetupService, Depends(get_workspace_setup_service)],
) -> WorkspaceSetupRunRead:
    return await service.get_setup_run(setup_run_id)


@router.post(
    "/runs/{setup_run_id}/steps/{step_key}",
    response_model=WorkspaceSetupRunRead,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_ADMIN))],
)
async def complete_workspace_setup_step(
    setup_run_id: UUID,
    step_key: WorkspaceSetupStepKey,
    payload: WorkspaceSetupStepRequest,
    service: Annotated[WorkspaceSetupService, Depends(get_workspace_setup_service)],
) -> WorkspaceSetupRunRead:
    return await service.complete_step(setup_run_id, step_key, payload.input)


@router.post(
    "/runs/{setup_run_id}/steps/{step_key}/skip",
    response_model=WorkspaceSetupRunRead,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_ADMIN))],
)
async def skip_workspace_setup_step(
    setup_run_id: UUID,
    step_key: WorkspaceSetupStepKey,
    service: Annotated[WorkspaceSetupService, Depends(get_workspace_setup_service)],
) -> WorkspaceSetupRunRead:
    return await service.skip_step(setup_run_id, step_key)


@router.post(
    "/runs/{setup_run_id}/finish",
    response_model=WorkspaceSetupRunRead,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_ADMIN))],
)
async def finish_workspace_setup(
    setup_run_id: UUID,
    service: Annotated[WorkspaceSetupService, Depends(get_workspace_setup_service)],
) -> WorkspaceSetupRunRead:
    return await service.finish_setup(setup_run_id)


@router.post(
    "/demo-workspace",
    response_model=WorkspaceSetupDemoWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_ADMIN))],
)
async def create_workspace_setup_demo_workspace(
    payload: WorkspaceSetupDemoWorkspaceRequest,
    service: Annotated[WorkspaceSetupService, Depends(get_workspace_setup_service)],
) -> WorkspaceSetupDemoWorkspaceResponse:
    return await service.create_demo_workspace(payload)
