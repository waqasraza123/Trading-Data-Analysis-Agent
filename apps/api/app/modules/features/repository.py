from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.features.models import FeatureSnapshot


class FeatureSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, snapshot: FeatureSnapshot) -> FeatureSnapshot:
        self.session.add(snapshot)
        await self.session.flush()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_by_analysis_run_id(self, analysis_run_id: UUID) -> FeatureSnapshot | None:
        statement: Select[tuple[FeatureSnapshot]] = (
            select(FeatureSnapshot)
            .where(FeatureSnapshot.analysis_run_id == analysis_run_id)
            .order_by(FeatureSnapshot.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()
