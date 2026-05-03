from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import AnalysisRun
from app.modules.intelligence_datasets.models import (
    IntelligenceDatasetExport,
    IntelligenceDatasetExportItem,
)
from app.modules.signals.models import Signal


class IntelligenceDatasetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_export(
        self,
        export: IntelligenceDatasetExport,
        items: list[IntelligenceDatasetExportItem],
    ) -> IntelligenceDatasetExport:
        self.session.add(export)
        await self.session.flush()
        await self.session.refresh(export)
        for item in items:
            item.export_id = export.id
            item.workspace_id = export.workspace_id
        self.session.add_all(items)
        await self.session.flush()
        await self.session.refresh(export)
        return export

    async def list_exports(self, workspace_id: UUID, limit: int, offset: int) -> list[IntelligenceDatasetExport]:
        statement: Select[tuple[IntelligenceDatasetExport]] = (
            select(IntelligenceDatasetExport)
            .where(IntelligenceDatasetExport.workspace_id == workspace_id)
            .order_by(IntelligenceDatasetExport.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_export(self, export_id: UUID) -> IntelligenceDatasetExport | None:
        return await self.session.get(IntelligenceDatasetExport, export_id)

    async def list_items(self, export_id: UUID, limit: int, offset: int) -> list[IntelligenceDatasetExportItem]:
        statement: Select[tuple[IntelligenceDatasetExportItem]] = (
            select(IntelligenceDatasetExportItem)
            .where(IntelligenceDatasetExportItem.export_id == export_id)
            .order_by(IntelligenceDatasetExportItem.sequence_number.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_signals(
        self,
        workspace_id: UUID,
        limit: int,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        strategy_profile_key: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[Signal]:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .join(AnalysisRun, AnalysisRun.id == Signal.analysis_run_id)
            .where(Signal.workspace_id == workspace_id)
            .order_by(Signal.created_at.asc())
            .limit(limit)
        )
        if symbol_id is not None:
            statement = statement.where(Signal.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(Signal.timeframe == timeframe)
        if strategy_profile_key is not None:
            statement = statement.where(Signal.strategy_profile_key == strategy_profile_key)
        if start_time is not None:
            statement = statement.where(AnalysisRun.end_time >= start_time)
        if end_time is not None:
            statement = statement.where(AnalysisRun.end_time <= end_time)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
