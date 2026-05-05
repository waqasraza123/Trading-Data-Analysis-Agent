from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.daily_routines.models import (
    DailyRoutineRun,
    DailyRoutineRunStatus,
    DailyRoutineRunStep,
    DailyRoutineTemplate,
)
from app.modules.intelligence_quality.models import IntelligenceQualityRun
from app.modules.outcomes.models import SignalOutcome
from app.modules.trading_journal.models import JournalEntry, JournalEntryReview
from app.modules.workspaces.models import Workspace


class DailyRoutineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_template(self, template: DailyRoutineTemplate) -> DailyRoutineTemplate:
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def update_template(self, template: DailyRoutineTemplate) -> DailyRoutineTemplate:
        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def get_template(self, template_id: UUID) -> DailyRoutineTemplate | None:
        return await self.session.get(DailyRoutineTemplate, template_id)

    async def get_template_by_key_version(
        self,
        key: str,
        routine_version: str,
        workspace_id: UUID | None = None,
    ) -> DailyRoutineTemplate | None:
        statement: Select[tuple[DailyRoutineTemplate]] = select(DailyRoutineTemplate).where(
            DailyRoutineTemplate.key == key,
            DailyRoutineTemplate.routine_version == routine_version,
        )
        if workspace_id is None:
            statement = statement.where(DailyRoutineTemplate.workspace_id.is_(None))
        else:
            statement = statement.where(DailyRoutineTemplate.workspace_id == workspace_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        workspace_id: UUID | None,
        routine_type: str | None,
        status: str | None,
    ) -> list[DailyRoutineTemplate]:
        statement: Select[tuple[DailyRoutineTemplate]] = select(DailyRoutineTemplate).order_by(
            DailyRoutineTemplate.routine_type.asc(),
            DailyRoutineTemplate.name.asc(),
        )
        if workspace_id is None:
            statement = statement.where(DailyRoutineTemplate.workspace_id.is_(None))
        else:
            statement = statement.where(
                or_(
                    DailyRoutineTemplate.workspace_id == workspace_id,
                    DailyRoutineTemplate.workspace_id.is_(None),
                )
            )
        if routine_type is not None:
            statement = statement.where(DailyRoutineTemplate.routine_type == routine_type)
        if status is not None:
            statement = statement.where(DailyRoutineTemplate.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_run(self, run: DailyRoutineRun) -> DailyRoutineRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run(self, run: DailyRoutineRun) -> DailyRoutineRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> DailyRoutineRun | None:
        return await self.session.get(DailyRoutineRun, run_id)

    async def list_runs(
        self,
        workspace_id: UUID,
        template_id: UUID | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[DailyRoutineRun]:
        statement: Select[tuple[DailyRoutineRun]] = (
            select(DailyRoutineRun)
            .where(DailyRoutineRun.workspace_id == workspace_id)
            .order_by(DailyRoutineRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if template_id is not None:
            statement = statement.where(DailyRoutineRun.template_id == template_id)
        if status is not None:
            statement = statement.where(DailyRoutineRun.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_active_run(
        self,
        workspace_id: UUID,
        template_id: UUID,
    ) -> DailyRoutineRun | None:
        statement: Select[tuple[DailyRoutineRun]] = (
            select(DailyRoutineRun)
            .where(
                DailyRoutineRun.workspace_id == workspace_id,
                DailyRoutineRun.template_id == template_id,
                DailyRoutineRun.status.in_(
                    [
                        DailyRoutineRunStatus.PENDING.value,
                        DailyRoutineRunStatus.RUNNING.value,
                    ]
                ),
            )
            .order_by(DailyRoutineRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_step(self, step: DailyRoutineRunStep) -> DailyRoutineRunStep:
        self.session.add(step)
        await self.session.flush()
        await self.session.refresh(step)
        return step

    async def update_step(self, step: DailyRoutineRunStep) -> DailyRoutineRunStep:
        await self.session.flush()
        await self.session.refresh(step)
        return step

    async def list_steps(self, routine_run_id: UUID) -> list[DailyRoutineRunStep]:
        statement: Select[tuple[DailyRoutineRunStep]] = (
            select(DailyRoutineRunStep)
            .where(DailyRoutineRunStep.routine_run_id == routine_run_id)
            .order_by(DailyRoutineRunStep.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        return await self.session.get(Workspace, workspace_id)

    async def count_recent_outcomes(
        self,
        workspace_id: UUID,
        period_start: datetime | None,
        period_end: datetime | None,
    ) -> dict[str, int]:
        statement = select(SignalOutcome.outcome_label, func.count(SignalOutcome.id)).where(
            SignalOutcome.workspace_id == workspace_id
        )
        if period_start is not None:
            statement = statement.where(SignalOutcome.created_at >= period_start)
        if period_end is not None:
            statement = statement.where(SignalOutcome.created_at <= period_end)
        result = await self.session.execute(statement.group_by(SignalOutcome.outcome_label))
        return {str(label): int(count) for label, count in result.all()}

    async def count_recent_quality_runs(
        self,
        workspace_id: UUID,
        period_start: datetime | None,
        period_end: datetime | None,
    ) -> dict[str, int]:
        statement = select(
            IntelligenceQualityRun.quality_label,
            func.count(IntelligenceQualityRun.id),
        ).where(IntelligenceQualityRun.workspace_id == workspace_id)
        if period_start is not None:
            statement = statement.where(IntelligenceQualityRun.created_at >= period_start)
        if period_end is not None:
            statement = statement.where(IntelligenceQualityRun.created_at <= period_end)
        result = await self.session.execute(
            statement.group_by(IntelligenceQualityRun.quality_label)
        )
        return {str(label): int(count) for label, count in result.all()}

    async def count_journal_follow_up(
        self,
        workspace_id: UUID,
        period_start: datetime | None,
        period_end: datetime | None,
    ) -> dict[str, int]:
        entries_statement = select(func.count(JournalEntry.id)).where(
            JournalEntry.workspace_id == workspace_id,
            JournalEntry.status != "archived",
        )
        reviews_statement = select(func.count(JournalEntryReview.id)).where(
            JournalEntryReview.workspace_id == workspace_id
        )
        if period_start is not None:
            entries_statement = entries_statement.where(JournalEntry.created_at >= period_start)
            reviews_statement = reviews_statement.where(
                JournalEntryReview.created_at >= period_start
            )
        if period_end is not None:
            entries_statement = entries_statement.where(JournalEntry.created_at <= period_end)
            reviews_statement = reviews_statement.where(JournalEntryReview.created_at <= period_end)
        entry_count = (await self.session.execute(entries_statement)).scalar_one()
        review_count = (await self.session.execute(reviews_statement)).scalar_one()
        return {
            "activeJournalEntryCount": int(entry_count or 0),
            "journalReviewCount": int(review_count or 0),
            "entriesWithoutReviewEstimate": max(int(entry_count or 0) - int(review_count or 0), 0),
        }
