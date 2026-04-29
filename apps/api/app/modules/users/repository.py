from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_workspace_email(self, workspace_id: UUID, email: str) -> User | None:
        statement = select(User).where(User.workspace_id == workspace_id, User.email == email)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list(self, limit: int, offset: int, workspace_id: UUID | None = None) -> list[User]:
        statement: Select[tuple[User]] = (
            select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(User.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
