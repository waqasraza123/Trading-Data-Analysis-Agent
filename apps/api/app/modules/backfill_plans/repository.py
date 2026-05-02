from uuid import UUID

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.backfill_plans.models import (
    BackfillItemStatus,
    BackfillPlanStatus,
    IntelligenceBackfillItem,
    IntelligenceBackfillPlan,
)


class BackfillPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_plan(self, plan: IntelligenceBackfillPlan) -> IntelligenceBackfillPlan:
        self.session.add(plan)
        await self.session.flush()
        await self.session.refresh(plan)
        return plan

    async def create_items(
        self,
        items: list[IntelligenceBackfillItem],
    ) -> list[IntelligenceBackfillItem]:
        self.session.add_all(items)
        await self.session.flush()
        for item in items:
            await self.session.refresh(item)
        return items

    async def get_plan(self, plan_id: UUID) -> IntelligenceBackfillPlan | None:
        return await self.session.get(IntelligenceBackfillPlan, plan_id)

    async def list_plans(
        self,
        workspace_id: UUID,
        plan_type: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[IntelligenceBackfillPlan]:
        statement: Select[tuple[IntelligenceBackfillPlan]] = (
            select(IntelligenceBackfillPlan)
            .where(IntelligenceBackfillPlan.workspace_id == workspace_id)
            .order_by(IntelligenceBackfillPlan.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if plan_type is not None:
            statement = statement.where(IntelligenceBackfillPlan.plan_type == plan_type)
        if status is not None:
            statement = statement.where(IntelligenceBackfillPlan.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_items(
        self,
        plan_id: UUID,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[IntelligenceBackfillItem]:
        statement: Select[tuple[IntelligenceBackfillItem]] = (
            select(IntelligenceBackfillItem)
            .where(IntelligenceBackfillItem.backfill_plan_id == plan_id)
            .order_by(
                IntelligenceBackfillItem.priority.desc(),
                IntelligenceBackfillItem.created_at.asc(),
                IntelligenceBackfillItem.id.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(IntelligenceBackfillItem.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def cancel_plan(self, plan: IntelligenceBackfillPlan) -> IntelligenceBackfillPlan:
        plan.status = BackfillPlanStatus.CANCELLED
        await self.session.execute(
            update(IntelligenceBackfillItem)
            .where(
                IntelligenceBackfillItem.backfill_plan_id == plan.id,
                IntelligenceBackfillItem.status.in_(
                    [BackfillItemStatus.PLANNED, BackfillItemStatus.QUEUED]
                ),
            )
            .values(status=BackfillItemStatus.CANCELLED)
        )
        await self.session.flush()
        await self.session.refresh(plan)
        return plan
