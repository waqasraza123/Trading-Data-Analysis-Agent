from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.outcomes.models import SignalOutcome
from app.modules.trading_journal.models import (
    JournalEntry,
    JournalEntryAttachment,
    JournalEntryReview,
)


class TradingJournalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_entry(self, entry: JournalEntry) -> JournalEntry:
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def get_entry(self, entry_id: UUID) -> JournalEntry | None:
        return await self.session.get(JournalEntry, entry_id)

    async def list_entries(
        self,
        workspace_id: UUID,
        user_id: UUID | None = None,
        signal_id: UUID | None = None,
        analysis_run_id: UUID | None = None,
        decision_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JournalEntry]:
        statement: Select[tuple[JournalEntry]] = select(JournalEntry).where(
            JournalEntry.workspace_id == workspace_id
        )
        if user_id is not None:
            statement = statement.where(JournalEntry.user_id == user_id)
        if signal_id is not None:
            statement = statement.where(JournalEntry.signal_id == signal_id)
        if analysis_run_id is not None:
            statement = statement.where(JournalEntry.analysis_run_id == analysis_run_id)
        if decision_type is not None:
            statement = statement.where(JournalEntry.decision_type == decision_type)
        if status is not None:
            statement = statement.where(JournalEntry.status == status)
        statement = statement.order_by(
            JournalEntry.created_at.desc(),
            JournalEntry.id.desc(),
        ).offset(offset).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_entry(self, entry: JournalEntry) -> JournalEntry:
        await self.session.flush()
        await self.session.refresh(entry)
        return entry

    async def create_attachment(
        self,
        attachment: JournalEntryAttachment,
    ) -> JournalEntryAttachment:
        self.session.add(attachment)
        await self.session.flush()
        await self.session.refresh(attachment)
        return attachment

    async def create_review(self, review: JournalEntryReview) -> JournalEntryReview:
        self.session.add(review)
        await self.session.flush()
        await self.session.refresh(review)
        return review

    async def list_reviews(self, entry_id: UUID) -> list[JournalEntryReview]:
        statement: Select[tuple[JournalEntryReview]] = (
            select(JournalEntryReview)
            .where(JournalEntryReview.journal_entry_id == entry_id)
            .order_by(JournalEntryReview.reviewed_at.desc(), JournalEntryReview.id.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_outcome(self, outcome_id: UUID) -> SignalOutcome | None:
        return await self.session.get(SignalOutcome, outcome_id)

    async def get_latest_outcome_for_signal(self, signal_id: UUID) -> SignalOutcome | None:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.signal_id == signal_id)
            .order_by(
                SignalOutcome.horizon_minutes.asc(),
                SignalOutcome.created_at.desc(),
                SignalOutcome.id.desc(),
            )
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
