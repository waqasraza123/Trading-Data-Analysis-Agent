from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chart_screenshots.models import ChartScreenshotRun


class ChartScreenshotRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, run: ChartScreenshotRun) -> ChartScreenshotRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_by_id(self, run_id: UUID) -> ChartScreenshotRun | None:
        return await self.session.get(ChartScreenshotRun, run_id)

    async def list_runs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        symbol_id: UUID | None = None,
        source_id: UUID | None = None,
        status: str | None = None,
    ) -> list[ChartScreenshotRun]:
        statement: Select[tuple[ChartScreenshotRun]] = (
            select(ChartScreenshotRun)
            .order_by(ChartScreenshotRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(ChartScreenshotRun.workspace_id == workspace_id)
        if symbol_id is not None:
            statement = statement.where(ChartScreenshotRun.symbol_id == symbol_id)
        if source_id is not None:
            statement = statement.where(ChartScreenshotRun.source_id == source_id)
        if status is not None:
            statement = statement.where(ChartScreenshotRun.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
