from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operator_reviews.models import (
    OperatorReviewEvent,
    OperatorReviewItem,
    OperatorReviewStatus,
)

ACTIVE_REVIEW_STATUSES = (
    OperatorReviewStatus.OPEN.value,
    OperatorReviewStatus.ASSIGNED.value,
    OperatorReviewStatus.IN_REVIEW.value,
)


class OperatorReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_item(self, item: OperatorReviewItem) -> OperatorReviewItem:
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def get_item(self, review_item_id: UUID) -> OperatorReviewItem | None:
        return await self.session.get(OperatorReviewItem, review_item_id)

    async def find_active_by_source(
        self,
        workspace_id: UUID,
        source_type: str,
        source_id: UUID,
        review_type: str,
    ) -> OperatorReviewItem | None:
        statement: Select[tuple[OperatorReviewItem]] = (
            select(OperatorReviewItem)
            .where(
                OperatorReviewItem.workspace_id == workspace_id,
                OperatorReviewItem.source_type == source_type,
                OperatorReviewItem.source_id == source_id,
                OperatorReviewItem.review_type == review_type,
                OperatorReviewItem.status.in_(ACTIVE_REVIEW_STATUSES),
            )
            .order_by(OperatorReviewItem.created_at.asc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_items(
        self,
        workspace_id: UUID,
        status: str | None = None,
        priority: str | None = None,
        review_type: str | None = None,
        source_type: str | None = None,
        assigned_to_user_id: UUID | None = None,
        related_signal_id: UUID | None = None,
        related_analysis_run_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OperatorReviewItem]:
        statement: Select[tuple[OperatorReviewItem]] = select(OperatorReviewItem).where(
            OperatorReviewItem.workspace_id == workspace_id
        )
        if status is not None:
            statement = statement.where(OperatorReviewItem.status == status)
        if priority is not None:
            statement = statement.where(OperatorReviewItem.priority == priority)
        if review_type is not None:
            statement = statement.where(OperatorReviewItem.review_type == review_type)
        if source_type is not None:
            statement = statement.where(OperatorReviewItem.source_type == source_type)
        if assigned_to_user_id is not None:
            statement = statement.where(
                OperatorReviewItem.assigned_to_user_id == assigned_to_user_id
            )
        if related_signal_id is not None:
            statement = statement.where(OperatorReviewItem.related_signal_id == related_signal_id)
        if related_analysis_run_id is not None:
            statement = statement.where(
                OperatorReviewItem.related_analysis_run_id == related_analysis_run_id
            )
        statement = (
            statement.order_by(
                OperatorReviewItem.created_at.desc(),
                OperatorReviewItem.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_item(self, item: OperatorReviewItem) -> OperatorReviewItem:
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def create_event(self, event: OperatorReviewEvent) -> OperatorReviewEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def list_events(self, review_item_id: UUID) -> list[OperatorReviewEvent]:
        statement: Select[tuple[OperatorReviewEvent]] = (
            select(OperatorReviewEvent)
            .where(OperatorReviewEvent.review_item_id == review_item_id)
            .order_by(OperatorReviewEvent.created_at.asc(), OperatorReviewEvent.id.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
