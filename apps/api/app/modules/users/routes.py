from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.users.schemas import UserCreate, UserRead, UserUpdate
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> UserService:
    return UserService(session)


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.USERS_ADMIN))],
)
async def create_user(
    payload: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    user = await service.create_user(payload)
    return UserRead.model_validate(user)


@router.get("", response_model=list[UserRead])
async def list_users(
    service: Annotated[UserService, Depends(get_user_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    workspace_id: UUID | None = None,
) -> list[UserRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    users = await service.list_users(
        limit=pagination.limit,
        offset=pagination.offset,
        workspace_id=workspace_id,
    )
    return [UserRead.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    user = await service.get_user(user_id)
    return UserRead.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permission(Permission.USERS_ADMIN))],
)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    user = await service.update_user(user_id, payload)
    return UserRead.model_validate(user)
