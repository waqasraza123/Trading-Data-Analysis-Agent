from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.workspaces.repository import WorkspaceRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = UserRepository(session)
        self.workspace_repository = WorkspaceRepository(session)

    async def create_user(self, payload: UserCreate) -> User:
        await self.validate_workspace(payload.workspace_id)
        user = User(**payload.model_dump(mode="python"))
        try:
            created_user = await self.repository.create(user)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(409, "user_conflict", "User already exists") from error
        return created_user

    async def list_users(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
    ) -> list[User]:
        return await self.repository.list(limit=limit, offset=offset, workspace_id=workspace_id)

    async def get_user(self, user_id: UUID) -> User:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise AppError(404, "user_not_found", "User not found")
        return user

    async def update_user(self, user_id: UUID, payload: UserUpdate) -> User:
        user = await self.get_user(user_id)
        updates = payload.model_dump(exclude_unset=True, mode="python")
        for field_name, field_value in updates.items():
            setattr(user, field_name, field_value)
        try:
            await self.session.flush()
            await self.session.refresh(user)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(409, "user_conflict", "User already exists") from error
        return user

    async def validate_workspace(self, workspace_id: UUID) -> None:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")
