from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workspaces.models import Workspace


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, workspace: Workspace) -> Workspace:
        self.session.add(workspace)
        await self.session.flush()
        await self.session.refresh(workspace)
        return workspace

    async def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        return await self.session.get(Workspace, workspace_id)

    async def get_by_name(self, name: str) -> Workspace | None:
        statement = select(Workspace).where(Workspace.name == name)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list(self, limit: int, offset: int) -> list[Workspace]:
        statement: Select[tuple[Workspace]] = (
            select(Workspace).order_by(Workspace.created_at.desc()).limit(limit).offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
