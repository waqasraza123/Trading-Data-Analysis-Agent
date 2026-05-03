from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.daily_workflows.models import (
    DailyWorkflowRun,
    DailyWorkflowRunStatus,
    DailyWorkflowStep,
)
from app.modules.market_scans.models import ScheduledScanConfig, ScheduledScanConfigStatus


class DailyWorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: DailyWorkflowRun) -> DailyWorkflowRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run(self, run: DailyWorkflowRun) -> DailyWorkflowRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> DailyWorkflowRun | None:
        return await self.session.get(DailyWorkflowRun, run_id)

    async def list_runs(
        self,
        workspace_id: UUID,
        workflow_type: str | None,
        status: str | None,
        watchlist_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[DailyWorkflowRun]:
        statement: Select[tuple[DailyWorkflowRun]] = (
            select(DailyWorkflowRun)
            .where(DailyWorkflowRun.workspace_id == workspace_id)
            .order_by(DailyWorkflowRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workflow_type is not None:
            statement = statement.where(DailyWorkflowRun.workflow_type == workflow_type)
        if status is not None:
            statement = statement.where(DailyWorkflowRun.status == status)
        if watchlist_id is not None:
            statement = statement.where(DailyWorkflowRun.watchlist_id == watchlist_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_active_run(
        self,
        workspace_id: UUID,
        workflow_type: str,
        watchlist_id: UUID | None,
    ) -> DailyWorkflowRun | None:
        statement: Select[tuple[DailyWorkflowRun]] = (
            select(DailyWorkflowRun)
            .where(
                DailyWorkflowRun.workspace_id == workspace_id,
                DailyWorkflowRun.workflow_type == workflow_type,
                DailyWorkflowRun.status.in_(
                    [
                        DailyWorkflowRunStatus.PENDING.value,
                        DailyWorkflowRunStatus.RUNNING.value,
                    ]
                ),
            )
            .order_by(DailyWorkflowRun.created_at.desc())
            .limit(1)
        )
        if watchlist_id is None:
            statement = statement.where(DailyWorkflowRun.watchlist_id.is_(None))
        else:
            statement = statement.where(DailyWorkflowRun.watchlist_id == watchlist_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_step(self, step: DailyWorkflowStep) -> DailyWorkflowStep:
        self.session.add(step)
        await self.session.flush()
        await self.session.refresh(step)
        return step

    async def update_step(self, step: DailyWorkflowStep) -> DailyWorkflowStep:
        await self.session.flush()
        await self.session.refresh(step)
        return step

    async def get_step_by_key(
        self,
        workflow_run_id: UUID,
        step_key: str,
    ) -> DailyWorkflowStep | None:
        statement: Select[tuple[DailyWorkflowStep]] = select(DailyWorkflowStep).where(
            DailyWorkflowStep.workflow_run_id == workflow_run_id,
            DailyWorkflowStep.step_key == step_key,
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_steps(self, workflow_run_id: UUID) -> list[DailyWorkflowStep]:
        statement: Select[tuple[DailyWorkflowStep]] = (
            select(DailyWorkflowStep)
            .where(DailyWorkflowStep.workflow_run_id == workflow_run_id)
            .order_by(DailyWorkflowStep.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_active_watchlist_scan_config(
        self,
        workspace_id: UUID,
        watchlist_id: UUID,
    ) -> ScheduledScanConfig | None:
        statement: Select[tuple[ScheduledScanConfig]] = (
            select(ScheduledScanConfig)
            .where(
                ScheduledScanConfig.workspace_id == workspace_id,
                ScheduledScanConfig.watchlist_id == watchlist_id,
                ScheduledScanConfig.status == ScheduledScanConfigStatus.ACTIVE.value,
            )
            .order_by(ScheduledScanConfig.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
