from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_plans.models import (
    ReasoningActionItem,
    ReasoningActionItemStatus,
    ReasoningActionPlan,
    ReasoningActionType,
    ReasoningActionWorkerRun,
    ReasoningActionWorkerRunStatus,
)

EXECUTABLE_ACTION_TYPES = {
    ReasoningActionType.EVALUATE_OUTCOME_AFTER_HORIZON.value,
    ReasoningActionType.RUN_REPLAY.value,
    ReasoningActionType.RUN_NEWS_CORRELATION.value,
    ReasoningActionType.WAIT_FOR_MORE_FINAL_CANDLES.value,
    ReasoningActionType.NO_ACTION.value,
}


class ReasoningActionPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_plan(self, plan: ReasoningActionPlan) -> ReasoningActionPlan:
        self.session.add(plan)
        await self.session.flush()
        await self.session.refresh(plan)
        return plan

    async def get_plan(self, plan_id: UUID) -> ReasoningActionPlan | None:
        return await self.session.get(ReasoningActionPlan, plan_id)

    async def get_latest_by_reasoning_run_id(
        self,
        reasoning_run_id: UUID,
    ) -> ReasoningActionPlan | None:
        statement: Select[tuple[ReasoningActionPlan]] = (
            select(ReasoningActionPlan)
            .where(ReasoningActionPlan.reasoning_run_id == reasoning_run_id)
            .order_by(ReasoningActionPlan.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def update_plan(self, plan: ReasoningActionPlan) -> ReasoningActionPlan:
        await self.session.flush()
        await self.session.refresh(plan)
        return plan

    async def create_item(self, item: ReasoningActionItem) -> ReasoningActionItem:
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def get_item(self, item_id: UUID) -> ReasoningActionItem | None:
        return await self.session.get(ReasoningActionItem, item_id)

    async def get_item_by_idempotency_key(
        self,
        workspace_id: UUID,
        idempotency_key: str,
    ) -> ReasoningActionItem | None:
        statement: Select[tuple[ReasoningActionItem]] = select(ReasoningActionItem).where(
            ReasoningActionItem.workspace_id == workspace_id,
            ReasoningActionItem.idempotency_key == idempotency_key,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_items(self, action_plan_id: UUID) -> list[ReasoningActionItem]:
        statement: Select[tuple[ReasoningActionItem]] = (
            select(ReasoningActionItem)
            .where(ReasoningActionItem.action_plan_id == action_plan_id)
            .order_by(ReasoningActionItem.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_due_items(
        self,
        now: datetime,
        limit: int,
        workspace_id: UUID | None = None,
    ) -> list[ReasoningActionItem]:
        statement: Select[tuple[ReasoningActionItem]] = (
            select(ReasoningActionItem)
            .where(
                ReasoningActionItem.status.in_(
                    [
                        ReasoningActionItemStatus.PENDING.value,
                        ReasoningActionItemStatus.DUE.value,
                    ]
                ),
                or_(ReasoningActionItem.due_at.is_(None), ReasoningActionItem.due_at <= now),
                ReasoningActionItem.attempts < ReasoningActionItem.max_attempts,
            )
            .order_by(
                ReasoningActionItem.due_at.asc().nullsfirst(),
                ReasoningActionItem.created_at.asc(),
            )
            .limit(limit)
        )
        if workspace_id is not None:
            statement = statement.where(ReasoningActionItem.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def claim_due_items(
        self,
        now: datetime,
        worker_id: str,
        limit: int,
        lock_seconds: int,
        max_attempts: int,
        workspace_id: UUID | None = None,
    ) -> list[ReasoningActionItem]:
        lock_until = now + timedelta(seconds=lock_seconds)
        statement: Select[tuple[ReasoningActionItem]] = (
            select(ReasoningActionItem)
            .where(
                ReasoningActionItem.action_type.in_(EXECUTABLE_ACTION_TYPES),
                ReasoningActionItem.attempts < ReasoningActionItem.max_attempts,
                ReasoningActionItem.attempts < max_attempts,
                or_(
                    and_(
                        ReasoningActionItem.status.in_(
                            [
                                ReasoningActionItemStatus.PENDING.value,
                                ReasoningActionItemStatus.DUE.value,
                            ]
                        ),
                        or_(
                            ReasoningActionItem.due_at.is_(None),
                            ReasoningActionItem.due_at <= now,
                        ),
                    ),
                    and_(
                        ReasoningActionItem.status == ReasoningActionItemStatus.RUNNING.value,
                        ReasoningActionItem.locked_until.is_not(None),
                        ReasoningActionItem.locked_until <= now,
                    ),
                ),
                or_(
                    ReasoningActionItem.locked_by.is_(None),
                    ReasoningActionItem.locked_until.is_(None),
                    ReasoningActionItem.locked_until <= now,
                ),
            )
            .order_by(
                ReasoningActionItem.due_at.asc().nullsfirst(),
                ReasoningActionItem.created_at.asc(),
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        if workspace_id is not None:
            statement = statement.where(ReasoningActionItem.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        items = list(result.scalars().all())
        for item in items:
            item.status = ReasoningActionItemStatus.RUNNING.value
            item.attempts += 1
            item.last_attempted_at = now
            item.locked_by = worker_id
            item.locked_until = lock_until
            item.error_code = None
            item.error_message = None
        await self.session.flush()
        return items

    async def list_pending_items_to_mark_due(
        self,
        now: datetime,
        workspace_id: UUID | None = None,
    ) -> list[ReasoningActionItem]:
        statement: Select[tuple[ReasoningActionItem]] = select(ReasoningActionItem).where(
            and_(
                ReasoningActionItem.status == ReasoningActionItemStatus.PENDING.value,
                or_(ReasoningActionItem.due_at.is_(None), ReasoningActionItem.due_at <= now),
            )
        )
        if workspace_id is not None:
            statement = statement.where(ReasoningActionItem.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_item(self, item: ReasoningActionItem) -> ReasoningActionItem:
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def create_worker_run(
        self,
        run: ReasoningActionWorkerRun,
    ) -> ReasoningActionWorkerRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_worker_run(
        self,
        run: ReasoningActionWorkerRun,
    ) -> ReasoningActionWorkerRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_latest_worker_run(
        self,
        worker_id: str | None = None,
    ) -> ReasoningActionWorkerRun | None:
        statement: Select[tuple[ReasoningActionWorkerRun]] = (
            select(ReasoningActionWorkerRun)
            .order_by(ReasoningActionWorkerRun.started_at.desc())
            .limit(1)
        )
        if worker_id is not None:
            statement = statement.where(ReasoningActionWorkerRun.worker_id == worker_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def count_items_by_status(
        self,
        status: ReasoningActionItemStatus,
        now: datetime,
        workspace_id: UUID | None = None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(ReasoningActionItem)
            .where(ReasoningActionItem.status == status.value)
        )
        if status == ReasoningActionItemStatus.DUE:
            statement = statement.where(
                or_(ReasoningActionItem.due_at.is_(None), ReasoningActionItem.due_at <= now)
            )
        if workspace_id is not None:
            statement = statement.where(ReasoningActionItem.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return int(result.scalar_one() or 0)

    async def oldest_due_at(
        self,
        now: datetime,
        workspace_id: UUID | None = None,
    ) -> datetime | None:
        statement = select(func.min(ReasoningActionItem.due_at)).where(
            ReasoningActionItem.status.in_(
                [
                    ReasoningActionItemStatus.PENDING.value,
                    ReasoningActionItemStatus.DUE.value,
                ]
            ),
            or_(ReasoningActionItem.due_at.is_(None), ReasoningActionItem.due_at <= now),
            ReasoningActionItem.action_type.in_(EXECUTABLE_ACTION_TYPES),
        )
        if workspace_id is not None:
            statement = statement.where(ReasoningActionItem.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_empty_worker_run(
        self,
        worker_id: str,
        batch_limit: int,
        started_at: datetime,
        workspace_id: UUID | None = None,
    ) -> ReasoningActionWorkerRun:
        return await self.create_worker_run(
            ReasoningActionWorkerRun(
                worker_id=worker_id,
                workspace_id=workspace_id,
                status=ReasoningActionWorkerRunStatus.RUNNING.value,
                batch_limit=batch_limit,
                claimed_count=0,
                completed_count=0,
                skipped_count=0,
                failed_count=0,
                started_at=started_at,
                metadata_json={},
            )
        )
