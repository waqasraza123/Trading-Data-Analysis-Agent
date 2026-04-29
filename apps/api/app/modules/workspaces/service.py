from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.schemas import WorkspaceCreate, WorkspaceUpdate


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = WorkspaceRepository(session)

    async def create_workspace(self, payload: WorkspaceCreate) -> Workspace:
        workspace = Workspace(**payload.model_dump(mode="python"))
        try:
            created_workspace = await self.repository.create(workspace)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "workspace_conflict",
                "Workspace could not be created",
            ) from error
        return created_workspace

    async def list_workspaces(self, limit: int, offset: int) -> list[Workspace]:
        return await self.repository.list(limit=limit, offset=offset)

    async def get_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = await self.repository.get_by_id(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")
        return workspace

    async def update_workspace(
        self,
        workspace_id: UUID,
        payload: WorkspaceUpdate,
    ) -> Workspace:
        workspace = await self.get_workspace(workspace_id)
        updates = payload.model_dump(exclude_unset=True, mode="python")
        for field_name, field_value in updates.items():
            setattr(workspace, field_name, field_value)
        try:
            await self.session.flush()
            await self.session.refresh(workspace)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "workspace_conflict",
                "Workspace could not be updated",
            ) from error
        return workspace
