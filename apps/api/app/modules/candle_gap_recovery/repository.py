from uuid import UUID

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candle_gap_recovery.models import (
    CandleGapRecoveryItem,
    CandleGapRecoveryItemStatus,
    CandleGapRecoveryPlan,
    CandleGapRecoveryPlanStatus,
)


class CandleGapRecoveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_plan(
        self,
        plan: CandleGapRecoveryPlan,
        items: list[CandleGapRecoveryItem],
    ) -> CandleGapRecoveryPlan:
        self.session.add(plan)
        await self.session.flush()
        for item in items:
            item.recovery_plan_id = plan.id
        self.session.add_all(items)
        await self.session.flush()
        await self.session.refresh(plan)
        return plan

    async def get_plan(self, plan_id: UUID) -> CandleGapRecoveryPlan | None:
        return await self.session.get(CandleGapRecoveryPlan, plan_id)

    async def list_items(
        self,
        plan_id: UUID,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[CandleGapRecoveryItem]:
        statement: Select[tuple[CandleGapRecoveryItem]] = (
            select(CandleGapRecoveryItem)
            .where(CandleGapRecoveryItem.recovery_plan_id == plan_id)
            .order_by(
                CandleGapRecoveryItem.gap_start_time.asc(),
                CandleGapRecoveryItem.id.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(CandleGapRecoveryItem.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_plan(self, plan: CandleGapRecoveryPlan) -> CandleGapRecoveryPlan:
        await self.session.flush()
        await self.session.refresh(plan)
        return plan

    async def update_item(self, item: CandleGapRecoveryItem) -> CandleGapRecoveryItem:
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def cancel_plan(self, plan: CandleGapRecoveryPlan) -> CandleGapRecoveryPlan:
        plan.status = CandleGapRecoveryPlanStatus.CANCELLED.value
        await self.session.execute(
            update(CandleGapRecoveryItem)
            .where(
                CandleGapRecoveryItem.recovery_plan_id == plan.id,
                CandleGapRecoveryItem.status.in_(
                    [
                        CandleGapRecoveryItemStatus.PLANNED.value,
                        CandleGapRecoveryItemStatus.QUEUED.value,
                    ]
                ),
            )
            .values(status=CandleGapRecoveryItemStatus.CANCELLED.value)
        )
        await self.session.flush()
        await self.session.refresh(plan)
        return plan
