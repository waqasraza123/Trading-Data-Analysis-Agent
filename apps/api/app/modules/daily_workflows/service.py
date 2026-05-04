from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.daily_workflows.models import (
    DailyWorkflowRun,
    DailyWorkflowRunStatus,
    DailyWorkflowStep,
)
from app.modules.daily_workflows.repository import DailyWorkflowRepository
from app.modules.daily_workflows.runner import DailyWorkflowRunner
from app.modules.daily_workflows.schemas import (
    DailyWorkflowRunListFilters,
    DailyWorkflowRunRequest,
)
from app.modules.market_scans.repository import MarketScanRepository
from app.modules.preference_profiles.repository import PreferenceProfileRepository
from app.modules.workspaces.repository import WorkspaceRepository

TERMINAL_WORKFLOW_STATUSES = {
    DailyWorkflowRunStatus.COMPLETED.value,
    DailyWorkflowRunStatus.COMPLETED_WITH_WARNINGS.value,
    DailyWorkflowRunStatus.FAILED.value,
    DailyWorkflowRunStatus.CANCELLED.value,
}


class DailyWorkflowService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = DailyWorkflowRepository(session)
        self.workspace_repository = WorkspaceRepository(session)
        self.market_scan_repository = MarketScanRepository(session)
        self.preference_profile_repository = PreferenceProfileRepository(session)

    async def run_workflow(self, payload: DailyWorkflowRunRequest) -> DailyWorkflowRun:
        await self.validate_request(payload)
        existing = await self.repository.get_active_run(
            workspace_id=payload.workspace_id,
            workflow_type=payload.workflow_type.value,
            watchlist_id=payload.watchlist_id,
        )
        if existing is not None:
            return existing
        run = DailyWorkflowRun(
            workspace_id=payload.workspace_id,
            workflow_type=payload.workflow_type.value,
            status=DailyWorkflowRunStatus.PENDING.value,
            workflow_version=self.settings.daily_workflow_version,
            watchlist_id=payload.watchlist_id,
            preference_profile_id=payload.preference_profile_id,
            period_start=payload.period_start,
            period_end=payload.period_end,
            filters_json=payload.filters_json
            | {"options": payload.options.model_dump(mode="json", by_alias=True)},
            steps_json=[],
            result_json={},
            created_artifact_ids_json={},
            summary="Daily workflow pending",
            started_at=utc_now(),
        )
        created = await self.repository.create_run(run)
        await self.session.commit()
        return await DailyWorkflowRunner(
            self.session,
            settings=self.settings,
            repository=self.repository,
        ).run(created, payload.options)

    async def list_runs(self, filters: DailyWorkflowRunListFilters) -> list[DailyWorkflowRun]:
        await self.validate_workspace(filters.workspace_id)
        return await self.repository.list_runs(
            workspace_id=filters.workspace_id,
            workflow_type=filters.workflow_type.value if filters.workflow_type else None,
            status=filters.status.value if filters.status else None,
            watchlist_id=filters.watchlist_id,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def get_run(self, run_id: UUID) -> DailyWorkflowRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "daily_workflow_run_not_found", "Daily workflow run not found")
        return run

    async def list_steps(self, run_id: UUID) -> list[DailyWorkflowStep]:
        await self.get_run(run_id)
        return await self.repository.list_steps(run_id)

    async def cancel_run(self, run_id: UUID) -> DailyWorkflowRun:
        run = await self.get_run(run_id)
        if run.status in TERMINAL_WORKFLOW_STATUSES:
            return run
        run.status = DailyWorkflowRunStatus.CANCELLED.value
        run.completed_at = utc_now()
        run.summary = "Daily workflow cancelled"
        updated = await self.repository.update_run(run)
        await self.session.commit()
        return updated

    async def validate_request(self, payload: DailyWorkflowRunRequest) -> None:
        await self.validate_workspace(payload.workspace_id)
        if payload.watchlist_id is not None:
            watchlist = await self.market_scan_repository.get_watchlist(payload.watchlist_id)
            if watchlist is None:
                raise AppError(404, "market_watchlist_not_found", "Watchlist not found")
            if watchlist.workspace_id != payload.workspace_id:
                raise AppError(
                    422,
                    "workspace_watchlist_mismatch",
                    "Watchlist does not belong to workspace",
                )
        if payload.preference_profile_id is not None:
            profile = await self.preference_profile_repository.get_by_id(
                payload.preference_profile_id
            )
            if profile is None:
                raise AppError(
                    404,
                    "preference_profile_not_found",
                    "Preference profile not found",
                )
            if profile.workspace_id != payload.workspace_id:
                raise AppError(
                    422,
                    "workspace_preference_profile_mismatch",
                    "Preference profile does not belong to workspace",
                )

    async def validate_workspace(self, workspace_id: UUID) -> None:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")
