from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engine_versions.models import EngineVersion


class EngineVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, engine_version: EngineVersion) -> EngineVersion:
        self.session.add(engine_version)
        await self.session.flush()
        await self.session.refresh(engine_version)
        return engine_version

    async def get_by_engine_version(
        self,
        engine_name: str,
        version: str,
    ) -> EngineVersion | None:
        statement = select(EngineVersion).where(
            EngineVersion.engine_name == engine_name,
            EngineVersion.version == version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_versions(self) -> list[EngineVersion]:
        statement: Select[tuple[EngineVersion]] = select(EngineVersion).order_by(
            EngineVersion.engine_name.asc(),
            EngineVersion.version.asc(),
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_engine_name(self, engine_name: str) -> list[EngineVersion]:
        statement: Select[tuple[EngineVersion]] = (
            select(EngineVersion)
            .where(EngineVersion.engine_name == engine_name)
            .order_by(EngineVersion.version.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
