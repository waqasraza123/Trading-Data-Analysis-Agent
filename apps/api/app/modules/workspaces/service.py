from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.auth.identity import IdentityContext
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.schemas import (
    WorkspaceCreate,
    WorkspaceDefaultContextRead,
    WorkspaceDefaultUserRead,
    WorkspaceRead,
    WorkspaceUpdate,
)


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

    async def get_default_context(
        self,
        identity: IdentityContext | None,
    ) -> WorkspaceDefaultContextRead:
        workspaces = await self.repository.list(limit=100, offset=0)
        workspace = identity.workspace if identity is not None and identity.workspace else None
        if workspace is None:
            workspace = workspaces[0] if workspaces else None
        if workspace is None:
            return WorkspaceDefaultContextRead(
                status="missing_workspace",
                workspace=None,
                user=None,
                available_workspaces=[],
            )
        user = identity.user if identity is not None and identity.user else None
        if user is None:
            result = await self.session.execute(
                select(User)
                .where(User.workspace_id == workspace.id)
                .order_by(User.created_at.asc())
                .limit(1)
            )
            user = result.scalar_one_or_none()
        return WorkspaceDefaultContextRead(
            status="ready",
            workspace=WorkspaceRead.model_validate(workspace),
            user=WorkspaceDefaultUserRead(id=user.id, role=user.role, name=user.name)
            if user is not None
            else None,
            available_workspaces=[WorkspaceRead.model_validate(item) for item in workspaces],
        )

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
