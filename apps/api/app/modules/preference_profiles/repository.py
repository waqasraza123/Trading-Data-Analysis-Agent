from uuid import UUID

from sqlalchemy import Select, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.market_sessions.models import MarketSessionContext
from app.modules.preference_profiles.models import (
    PersonalStrategyPreferenceProfile,
    PreferenceProfileStatus,
)
from app.modules.setup_context.models import SetupContext
from app.modules.signals.models import Signal
from app.modules.symbols.models import Symbol
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace


class PreferenceProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        profile: PersonalStrategyPreferenceProfile,
    ) -> PersonalStrategyPreferenceProfile:
        self.session.add(profile)
        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    async def get_by_id(self, profile_id: UUID) -> PersonalStrategyPreferenceProfile | None:
        return await self.session.get(PersonalStrategyPreferenceProfile, profile_id)

    async def list_profiles(
        self,
        workspace_id: UUID,
        user_id: UUID | None,
        status: str | None,
        include_archived: bool,
        limit: int,
        offset: int,
    ) -> list[PersonalStrategyPreferenceProfile]:
        statement: Select[tuple[PersonalStrategyPreferenceProfile]] = (
            select(PersonalStrategyPreferenceProfile)
            .where(PersonalStrategyPreferenceProfile.workspace_id == workspace_id)
            .order_by(
                PersonalStrategyPreferenceProfile.is_default.desc(),
                PersonalStrategyPreferenceProfile.updated_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        if user_id is not None:
            statement = statement.where(
                or_(
                    PersonalStrategyPreferenceProfile.user_id == user_id,
                    PersonalStrategyPreferenceProfile.user_id.is_(None),
                )
            )
        if status is not None:
            statement = statement.where(PersonalStrategyPreferenceProfile.status == status)
        elif not include_archived:
            statement = statement.where(
                PersonalStrategyPreferenceProfile.status != PreferenceProfileStatus.ARCHIVED.value
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update(
        self,
        profile: PersonalStrategyPreferenceProfile,
    ) -> PersonalStrategyPreferenceProfile:
        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    async def clear_default_profiles(self, workspace_id: UUID, except_profile_id: UUID) -> None:
        await self.session.execute(
            update(PersonalStrategyPreferenceProfile)
            .where(
                PersonalStrategyPreferenceProfile.workspace_id == workspace_id,
                PersonalStrategyPreferenceProfile.id != except_profile_id,
                PersonalStrategyPreferenceProfile.is_default.is_(True),
            )
            .values(is_default=False)
        )
        await self.session.flush()

    async def get_default_profile(
        self,
        workspace_id: UUID,
        user_id: UUID | None = None,
    ) -> PersonalStrategyPreferenceProfile | None:
        statement: Select[tuple[PersonalStrategyPreferenceProfile]] = (
            select(PersonalStrategyPreferenceProfile)
            .where(
                PersonalStrategyPreferenceProfile.workspace_id == workspace_id,
                PersonalStrategyPreferenceProfile.status == PreferenceProfileStatus.ACTIVE.value,
                PersonalStrategyPreferenceProfile.is_default.is_(True),
            )
            .order_by(PersonalStrategyPreferenceProfile.updated_at.desc())
        )
        if user_id is not None:
            statement = statement.where(
                or_(
                    PersonalStrategyPreferenceProfile.user_id == user_id,
                    PersonalStrategyPreferenceProfile.user_id.is_(None),
                )
            )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        return await self.session.get(Workspace, workspace_id)

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_symbol(self, symbol_id: UUID) -> Symbol | None:
        return await self.session.get(Symbol, symbol_id)

    async def get_signal(self, signal_id: UUID) -> Signal | None:
        return await self.session.get(Signal, signal_id)

    async def get_latest_setup_context(self, signal_id: UUID) -> SetupContext | None:
        statement: Select[tuple[SetupContext]] = (
            select(SetupContext)
            .where(SetupContext.signal_id == signal_id)
            .order_by(SetupContext.updated_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_market_session(self, signal: Signal) -> MarketSessionContext | None:
        statement: Select[tuple[MarketSessionContext]] = (
            select(MarketSessionContext)
            .where(
                or_(
                    MarketSessionContext.signal_id == signal.id,
                    MarketSessionContext.analysis_run_id == signal.analysis_run_id,
                )
            )
            .order_by(MarketSessionContext.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_market_memory(self, signal: Signal) -> RollingMarketStateSnapshot | None:
        statement: Select[tuple[RollingMarketStateSnapshot]] = (
            select(RollingMarketStateSnapshot)
            .where(
                RollingMarketStateSnapshot.workspace_id == signal.workspace_id,
                RollingMarketStateSnapshot.symbol_id == signal.symbol_id,
                RollingMarketStateSnapshot.timeframe == signal.timeframe,
            )
            .order_by(
                (RollingMarketStateSnapshot.latest_signal_id == signal.id).desc(),
                RollingMarketStateSnapshot.updated_at.desc(),
            )
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()
