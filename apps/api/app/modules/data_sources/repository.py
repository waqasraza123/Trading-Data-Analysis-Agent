from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_sources.models import DataSource


class DataSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data_source: DataSource) -> DataSource:
        self.session.add(data_source)
        await self.session.flush()
        await self.session.refresh(data_source)
        return data_source

    async def get_by_id(self, data_source_id: UUID) -> DataSource | None:
        return await self.session.get(DataSource, data_source_id)

    async def list(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> list[DataSource]:
        statement: Select[tuple[DataSource]] = (
            select(DataSource).order_by(DataSource.created_at.desc()).limit(limit).offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(DataSource.workspace_id == workspace_id)
        if source_type is not None:
            statement = statement.where(DataSource.source_type == source_type)
        if status is not None:
            statement = statement.where(DataSource.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count(
        self,
        workspace_id: UUID | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> int:
        statement = select(func.count()).select_from(DataSource)
        if workspace_id is not None:
            statement = statement.where(DataSource.workspace_id == workspace_id)
        if source_type is not None:
            statement = statement.where(DataSource.source_type == source_type)
        if status is not None:
            statement = statement.where(DataSource.status == status)
        result = await self.session.execute(statement)
        return int(result.scalar_one())
