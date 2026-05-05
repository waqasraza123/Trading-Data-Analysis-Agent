from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.preference_profiles.models import PreferenceProfileStatus
from app.modules.preference_profiles.schemas import (
    PreferenceProfileCreate,
    PreferenceProfileFilterContextRead,
    PreferenceProfileMatchRead,
    PreferenceProfileRead,
    PreferenceProfileUpdate,
)
from app.modules.preference_profiles.service import PreferenceProfileService

router = APIRouter(prefix="/preference-profiles", tags=["preference-profiles"])


def get_preference_profile_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> PreferenceProfileService:
    return PreferenceProfileService(session)


@router.post(
    "",
    response_model=PreferenceProfileRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.PREFERENCES_WRITE))],
)
async def create_preference_profile(
    payload: PreferenceProfileCreate,
    service: Annotated[PreferenceProfileService, Depends(get_preference_profile_service)],
) -> PreferenceProfileRead:
    profile = await service.create_preference_profile(payload)
    return PreferenceProfileRead.model_validate(profile)


@router.get("", response_model=list[PreferenceProfileRead])
async def list_preference_profiles(
    service: Annotated[PreferenceProfileService, Depends(get_preference_profile_service)],
    workspace_id: Annotated[UUID, Query(alias="workspaceId")],
    user_id: Annotated[UUID | None, Query(alias="userId")] = None,
    status_filter: Annotated[PreferenceProfileStatus | None, Query(alias="status")] = None,
    include_archived: Annotated[bool, Query(alias="includeArchived")] = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PreferenceProfileRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    profiles = await service.list_preference_profiles(
        workspace_id=workspace_id,
        user_id=user_id,
        status=status_filter,
        include_archived=include_archived,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [PreferenceProfileRead.model_validate(profile) for profile in profiles]


@router.get("/default", response_model=PreferenceProfileRead)
async def get_default_preference_profile(
    service: Annotated[PreferenceProfileService, Depends(get_preference_profile_service)],
    workspace_id: Annotated[UUID, Query(alias="workspaceId")],
    user_id: Annotated[UUID | None, Query(alias="userId")] = None,
) -> PreferenceProfileRead:
    profile = await service.get_default_preference_profile(workspace_id, user_id)
    return PreferenceProfileRead.model_validate(profile)


@router.get("/{profile_id}", response_model=PreferenceProfileRead)
async def get_preference_profile(
    profile_id: UUID,
    service: Annotated[PreferenceProfileService, Depends(get_preference_profile_service)],
) -> PreferenceProfileRead:
    profile = await service.get_preference_profile(profile_id)
    return PreferenceProfileRead.model_validate(profile)


@router.patch(
    "/{profile_id}",
    response_model=PreferenceProfileRead,
    dependencies=[Depends(require_permission(Permission.PREFERENCES_WRITE))],
)
async def update_preference_profile(
    profile_id: UUID,
    payload: PreferenceProfileUpdate,
    service: Annotated[PreferenceProfileService, Depends(get_preference_profile_service)],
) -> PreferenceProfileRead:
    profile = await service.update_preference_profile(profile_id, payload)
    return PreferenceProfileRead.model_validate(profile)


@router.post(
    "/{profile_id}/archive",
    response_model=PreferenceProfileRead,
    dependencies=[Depends(require_permission(Permission.PREFERENCES_WRITE))],
)
async def archive_preference_profile(
    profile_id: UUID,
    service: Annotated[PreferenceProfileService, Depends(get_preference_profile_service)],
) -> PreferenceProfileRead:
    profile = await service.archive_preference_profile(profile_id)
    return PreferenceProfileRead.model_validate(profile)


@router.post(
    "/{profile_id}/set-default",
    response_model=PreferenceProfileRead,
    dependencies=[Depends(require_permission(Permission.PREFERENCES_WRITE))],
)
async def set_default_preference_profile(
    profile_id: UUID,
    service: Annotated[PreferenceProfileService, Depends(get_preference_profile_service)],
) -> PreferenceProfileRead:
    profile = await service.set_default_profile(profile_id)
    return PreferenceProfileRead.model_validate(profile)


@router.get("/{profile_id}/filter-context", response_model=PreferenceProfileFilterContextRead)
async def get_preference_profile_filter_context(
    profile_id: UUID,
    service: Annotated[PreferenceProfileService, Depends(get_preference_profile_service)],
) -> PreferenceProfileFilterContextRead:
    return await service.build_filter_context(profile_id)


@router.post(
    "/{profile_id}/match-signal/{signal_id}",
    response_model=PreferenceProfileMatchRead,
    dependencies=[Depends(require_permission(Permission.PREFERENCES_WRITE))],
)
async def match_preference_profile_signal(
    profile_id: UUID,
    signal_id: UUID,
    service: Annotated[PreferenceProfileService, Depends(get_preference_profile_service)],
) -> PreferenceProfileMatchRead:
    return await service.match_signal(profile_id, signal_id)
