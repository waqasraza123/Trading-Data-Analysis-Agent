from typing import Annotated

from fastapi import APIRouter, Body, Request, status

from app.core.errors import AppError
from app.db.session import get_async_session_factory
from app.modules.demo_mode.schemas import (
    DemoModeRunFullFlowResponse,
    DemoModeRunRequest,
    DemoModeStatusResponse,
    DemoModeWorkspaceRequest,
    DemoModeWorkspaceResponse,
)
from app.modules.demo_mode.service import (
    DemoModeService,
    demo_mode_availability,
    demo_mode_status_response,
    disabled_flow_response,
    disabled_workspace_response,
)

router = APIRouter(prefix="/demo-mode", tags=["demo-mode"])


@router.get("/status", response_model=DemoModeStatusResponse)
async def get_demo_mode_status(request: Request) -> DemoModeStatusResponse:
    return demo_mode_status_response(request.app.state.settings)


@router.post(
    "/workspace",
    response_model=DemoModeWorkspaceResponse,
    status_code=status.HTTP_200_OK,
)
async def create_demo_workspace(
    payload: Annotated[DemoModeWorkspaceRequest, Body(default_factory=DemoModeWorkspaceRequest)],
    request: Request,
) -> DemoModeWorkspaceResponse:
    settings = request.app.state.settings
    enabled, _ = demo_mode_availability(settings)
    if not enabled:
        return disabled_workspace_response(settings)
    session_factory = get_async_session_factory()
    if session_factory is None:
        raise AppError(503, "database_not_configured", "DATABASE_URL is not configured")
    async with session_factory() as session:
        return await DemoModeService(session, settings).create_demo_workspace(payload)


@router.post(
    "/run-full-flow",
    response_model=DemoModeRunFullFlowResponse,
    status_code=status.HTTP_200_OK,
)
async def run_full_demo_flow(
    payload: Annotated[DemoModeRunRequest, Body(default_factory=DemoModeRunRequest)],
    request: Request,
) -> DemoModeRunFullFlowResponse:
    settings = request.app.state.settings
    enabled, _ = demo_mode_availability(settings)
    if not enabled:
        return disabled_flow_response(settings)
    session_factory = get_async_session_factory()
    if session_factory is None:
        raise AppError(503, "database_not_configured", "DATABASE_URL is not configured")
    async with session_factory() as session:
        return await DemoModeService(session, settings).run_full_demo_flow(payload)
