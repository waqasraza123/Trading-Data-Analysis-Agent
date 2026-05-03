from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.profile_governance.models import (
    StrategyProfileDraft,
    StrategyProfileDraftEvent,
)
from app.modules.strategy_profiles.models import StrategyProfile


class StrategyProfileDraftRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_draft(self, draft: StrategyProfileDraft) -> StrategyProfileDraft:
        self.session.add(draft)
        await self.session.flush()
        await self.session.refresh(draft)
        return draft

    async def get_draft(self, draft_id: UUID) -> StrategyProfileDraft | None:
        return await self.session.get(StrategyProfileDraft, draft_id)

    async def list_drafts(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        status: str | None = None,
        draft_key: str | None = None,
        base_strategy_profile_key: str | None = None,
    ) -> list[StrategyProfileDraft]:
        statement: Select[tuple[StrategyProfileDraft]] = (
            select(StrategyProfileDraft)
            .order_by(StrategyProfileDraft.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(StrategyProfileDraft.workspace_id == workspace_id)
        if status is not None:
            statement = statement.where(StrategyProfileDraft.status == status)
        if draft_key is not None:
            statement = statement.where(StrategyProfileDraft.draft_key == draft_key)
        if base_strategy_profile_key is not None:
            statement = statement.where(
                StrategyProfileDraft.base_strategy_profile_key == base_strategy_profile_key
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_draft(self, draft: StrategyProfileDraft) -> StrategyProfileDraft:
        await self.session.flush()
        await self.session.refresh(draft)
        return draft

    async def create_event(self, event: StrategyProfileDraftEvent) -> StrategyProfileDraftEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def list_events(self, draft_id: UUID) -> list[StrategyProfileDraftEvent]:
        statement: Select[tuple[StrategyProfileDraftEvent]] = (
            select(StrategyProfileDraftEvent)
            .where(StrategyProfileDraftEvent.draft_id == draft_id)
            .order_by(StrategyProfileDraftEvent.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_strategy_profile(self, strategy_profile_id: UUID) -> StrategyProfile | None:
        return await self.session.get(StrategyProfile, strategy_profile_id)

    async def get_strategy_profile_by_key_version(
        self,
        key: str,
        version: str,
    ) -> StrategyProfile | None:
        statement = select(StrategyProfile).where(
            StrategyProfile.key == key,
            StrategyProfile.version == version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_strategy_profile_by_key(
        self,
        key: str,
        active_only: bool = False,
    ) -> StrategyProfile | None:
        statement: Select[tuple[StrategyProfile]] = (
            select(StrategyProfile)
            .where(StrategyProfile.key == key)
            .order_by(StrategyProfile.version.desc())
            .limit(1)
        )
        if active_only:
            statement = statement.where(StrategyProfile.is_active.is_(True))
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_active_strategy_profiles_by_key(self, key: str) -> list[StrategyProfile]:
        statement: Select[tuple[StrategyProfile]] = (
            select(StrategyProfile)
            .where(StrategyProfile.key == key, StrategyProfile.is_active.is_(True))
            .order_by(StrategyProfile.version.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_strategy_profile(self, profile: StrategyProfile) -> StrategyProfile:
        self.session.add(profile)
        await self.session.flush()
        await self.session.refresh(profile)
        return profile
