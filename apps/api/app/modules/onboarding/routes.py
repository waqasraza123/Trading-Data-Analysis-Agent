from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.onboarding.schemas import (
    OnboardingActionRequest,
    OnboardingActionResponse,
    OnboardingStatusResponse,
)
from app.modules.onboarding.service import OnboardingService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def get_onboarding_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> OnboardingService:
    return OnboardingService(session=session, settings=request.app.state.settings)


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    service: Annotated[OnboardingService, Depends(get_onboarding_service)],
    workspace_id: Annotated[UUID | None, Query(alias="workspaceId")] = None,
    user_id: Annotated[UUID | None, Query(alias="userId")] = None,
) -> OnboardingStatusResponse:
    return await service.get_status(workspace_id=workspace_id, user_id=user_id)


@router.post(
    "/actions",
    response_model=OnboardingActionResponse,
    dependencies=[Depends(require_permission(Permission.WORKSPACE_ADMIN))],
)
async def run_onboarding_action(
    payload: OnboardingActionRequest,
    service: Annotated[OnboardingService, Depends(get_onboarding_service)],
) -> OnboardingActionResponse:
    return await service.run_action(payload)
