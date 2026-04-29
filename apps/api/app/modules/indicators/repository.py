from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.indicators.models import IndicatorSnapshot


class IndicatorSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, snapshot: IndicatorSnapshot) -> IndicatorSnapshot:
        self.session.add(snapshot)
        await self.session.flush()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_by_analysis_run_id(self, analysis_run_id: UUID) -> IndicatorSnapshot | None:
        statement: Select[tuple[IndicatorSnapshot]] = (
            select(IndicatorSnapshot)
            .where(IndicatorSnapshot.analysis_run_id == analysis_run_id)
            .order_by(IndicatorSnapshot.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()
