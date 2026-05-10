from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, analysis_run: AnalysisRun) -> AnalysisRun:
        self.session.add(analysis_run)
        await self.session.flush()
        await self.session.refresh(analysis_run)
        return analysis_run

    async def get_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        return await self.session.get(AnalysisRun, analysis_run_id)

    async def list_runs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        symbol_id: UUID | None = None,
        status: str | None = None,
        analysis_mode: str | None = None,
        replayed_from_analysis_run_id: UUID | None = None,
    ) -> list[AnalysisRun]:
        statement: Select[tuple[AnalysisRun]] = (
            select(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(limit).offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(AnalysisRun.workspace_id == workspace_id)
        if symbol_id is not None:
            statement = statement.where(AnalysisRun.symbol_id == symbol_id)
        if status is not None:
            statement = statement.where(AnalysisRun.status == status)
        if analysis_mode is not None:
            statement = statement.where(AnalysisRun.analysis_mode == analysis_mode)
        if replayed_from_analysis_run_id is not None:
            statement = statement.where(
                AnalysisRun.replayed_from_analysis_run_id == replayed_from_analysis_run_id
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def add_audit_log(self, audit_log: AnalysisAuditLog) -> AnalysisAuditLog:
        self.session.add(audit_log)
        await self.session.flush()
        await self.session.refresh(audit_log)
        return audit_log

    async def list_audit_logs(self, analysis_run_id: UUID) -> list[AnalysisAuditLog]:
        statement: Select[tuple[AnalysisAuditLog]] = (
            select(AnalysisAuditLog)
            .where(AnalysisAuditLog.analysis_run_id == analysis_run_id)
            .order_by(AnalysisAuditLog.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
