from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.strategy_profiles.models import StrategyProfile


class StrategyProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_profiles(
        self,
        limit: int,
        offset: int,
        is_active: bool | None = None,
    ) -> list[StrategyProfile]:
        statement: Select[tuple[StrategyProfile]] = (
            select(StrategyProfile)
            .order_by(StrategyProfile.key.asc(), StrategyProfile.version.asc())
            .limit(limit)
            .offset(offset)
        )
        if is_active is not None:
            statement = statement.where(StrategyProfile.is_active == is_active)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_active_profiles(self) -> list[StrategyProfile]:
        statement: Select[tuple[StrategyProfile]] = (
            select(StrategyProfile)
            .where(StrategyProfile.is_active.is_(True))
            .order_by(StrategyProfile.key.asc(), StrategyProfile.version.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, strategy_profile_id: UUID) -> StrategyProfile | None:
        return await self.session.get(StrategyProfile, strategy_profile_id)

    async def get_by_key(
        self,
        key: str,
        active_only: bool = False,
    ) -> StrategyProfile | None:
        statement: Select[tuple[StrategyProfile]] = (
            select(StrategyProfile)
            .where(StrategyProfile.key == key)
            .order_by(StrategyProfile.version.desc())
        )
        if active_only:
            statement = statement.where(StrategyProfile.is_active.is_(True))
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_by_key_version(self, key: str, version: str) -> StrategyProfile | None:
        statement = select(StrategyProfile).where(
            StrategyProfile.key == key,
            StrategyProfile.version == version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, strategy_profile: StrategyProfile) -> StrategyProfile:
        self.session.add(strategy_profile)
        await self.session.flush()
        await self.session.refresh(strategy_profile)
        return strategy_profile
