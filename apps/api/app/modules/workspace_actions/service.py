from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.daily_briefs.schemas import DailyBriefFilters
from app.modules.daily_briefs.service import DailyBriefService
from app.modules.daily_workflows.models import DailyWorkflowType
from app.modules.daily_workflows.schemas import DailyWorkflowOptions, DailyWorkflowRunRequest
from app.modules.daily_workflows.service import DailyWorkflowService
from app.modules.market_memory.service import MarketMemoryService
from app.modules.product_readiness.repository import ProductReadinessRepository
from app.modules.product_readiness.service import ProductReadinessService
from app.modules.provider_health.service import ProviderHealthService
from app.modules.signal_priority.service import SignalPriorityService
from app.modules.workspace_actions.schemas import (
    WorkspaceQuickActionRequest,
    WorkspaceQuickActionResponse,
)
from app.modules.workspaces.repository import WorkspaceRepository

ALLOWED_ACTIONS = {
    "run_daily_workflow",
    "refresh_provider_health",
    "generate_daily_brief",
    "score_recent_signals",
    "refresh_market_memory",
    "run_product_readiness",
}
UNSAFE_ACTIONS = {
    "buy",
    "sell",
    "enter_trade",
    "exit_trade",
    "place_order",
    "execute_trade",
    "use_leverage",
    "broker_order",
    "auto_trade",
}


class WorkspaceQuickActionService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.workspace_repository = WorkspaceRepository(session)

    async def run_action(
        self,
        workspace_id: UUID,
        payload: WorkspaceQuickActionRequest,
    ) -> WorkspaceQuickActionResponse:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")
        action_type = normalize_action_type(payload.action_type)
        if action_type in UNSAFE_ACTIONS:
            raise AppError(
                400, "unsafe_action_rejected", "Action is outside product safety boundary"
            )
        if action_type not in ALLOWED_ACTIONS:
            raise AppError(
                400,
                "unsupported_action",
                "This backend-safe quick action is not available.",
            )
        if action_type == "run_daily_workflow":
            return await self.run_daily_workflow(workspace_id, payload)
        if action_type == "refresh_provider_health":
            return await self.refresh_provider_health(workspace_id, payload)
        if action_type == "generate_daily_brief":
            return await self.generate_daily_brief(workspace_id, payload)
        if action_type == "score_recent_signals":
            return await self.score_recent_signals(workspace_id, payload)
        if action_type == "refresh_market_memory":
            return await self.refresh_market_memory(workspace_id, payload)
        return await self.run_product_readiness(workspace_id, payload)

    async def run_daily_workflow(
        self,
        workspace_id: UUID,
        payload: WorkspaceQuickActionRequest,
    ) -> WorkspaceQuickActionResponse:
        options = DailyWorkflowOptions(
            allow_provider_polling=bool(
                option_value(payload.options, "allow_provider_polling", False)
            ),
            force=bool(option_value(payload.options, "force", False)),
        )
        run = await DailyWorkflowService(self.session, settings=self.settings).run_workflow(
            DailyWorkflowRunRequest(
                workspace_id=workspace_id,
                workflow_type=DailyWorkflowType.DAILY_SCAN,
                watchlist_id=payload.watchlist_id,
                preference_profile_id=payload.preference_profile_id,
                options=options,
                filters_json={"quickAction": True},
            )
        )
        return WorkspaceQuickActionResponse(
            workspace_id=workspace_id,
            action_type="run_daily_workflow",
            status=run.status,
            summary=run.summary,
            created_artifact_ids_json={
                "dailyWorkflowRunId": str(run.id),
                **run.created_artifact_ids_json,
            },
            result_json=run.result_json,
        )

    async def refresh_provider_health(
        self,
        workspace_id: UUID,
        payload: WorkspaceQuickActionRequest,
    ) -> WorkspaceQuickActionResponse:
        limit = bounded_int(
            option_value(payload.options, "limit", 500), default=500, minimum=1, maximum=500
        )
        snapshots, skipped_count = await ProviderHealthService(
            self.session, settings=self.settings
        ).build_workspace_health(
            workspace_id=workspace_id,
            limit=limit,
        )
        return WorkspaceQuickActionResponse(
            workspace_id=workspace_id,
            action_type="refresh_provider_health",
            status="completed",
            summary=f"Provider health refreshed for {len(snapshots)} contexts.",
            created_artifact_ids_json={
                "providerHealthSnapshotIds": [str(snapshot.id) for snapshot in snapshots]
            },
            result_json={"refreshedCount": len(snapshots), "skippedCount": skipped_count},
        )

    async def generate_daily_brief(
        self,
        workspace_id: UUID,
        payload: WorkspaceQuickActionRequest,
    ) -> WorkspaceQuickActionResponse:
        brief_date = parse_date_option(payload.options.get("date")) or datetime.now(UTC).date()
        run = await DailyBriefService(self.session, settings=self.settings).create_daily_brief(
            workspace_id=workspace_id,
            brief_date=brief_date,
            timezone=str(
                option_value(
                    payload.options, "timezone", self.settings.daily_brief_default_timezone
                )
            ),
            filters=DailyBriefFilters(preference_profile_id=payload.preference_profile_id),
        )
        return WorkspaceQuickActionResponse(
            workspace_id=workspace_id,
            action_type="generate_daily_brief",
            status=run.status,
            summary=str(run.summary_json.get("summary") or f"Daily brief {run.status}."),
            created_artifact_ids_json={"dailyBriefRunId": str(run.id)},
            result_json={
                "generatedAt": run.generated_at.isoformat(),
                "warnings": run.warnings_json,
            },
        )

    async def score_recent_signals(
        self,
        workspace_id: UUID,
        payload: WorkspaceQuickActionRequest,
    ) -> WorkspaceQuickActionResponse:
        limit = bounded_int(
            option_value(payload.options, "limit", 500), default=500, minimum=1, maximum=1000
        )
        scores = await SignalPriorityService(
            self.session, settings=self.settings
        ).score_workspace_recent_signals(
            workspace_id=workspace_id,
            limit=limit,
            force_recompute=bool(option_value(payload.options, "force", False)),
        )
        return WorkspaceQuickActionResponse(
            workspace_id=workspace_id,
            action_type="score_recent_signals",
            status="completed",
            summary=f"Signal priority scored for {len(scores)} stored signals.",
            created_artifact_ids_json={
                "signalPriorityScoreIds": [str(score.id) for score in scores]
            },
            result_json={"scoredCount": len(scores)},
        )

    async def refresh_market_memory(
        self,
        workspace_id: UUID,
        payload: WorkspaceQuickActionRequest,
    ) -> WorkspaceQuickActionResponse:
        limit = bounded_int(
            option_value(payload.options, "limit", 500), default=500, minimum=1, maximum=1000
        )
        snapshots = await MarketMemoryService(
            self.session, settings=self.settings
        ).refresh_workspace_snapshots(
            workspace_id=workspace_id,
            limit=limit,
        )
        return WorkspaceQuickActionResponse(
            workspace_id=workspace_id,
            action_type="refresh_market_memory",
            status="completed",
            summary=f"Market memory refreshed for {len(snapshots)} contexts.",
            created_artifact_ids_json={
                "marketMemorySnapshotIds": [str(snapshot.id) for snapshot in snapshots]
            },
            result_json={"refreshedCount": len(snapshots)},
        )

    async def run_product_readiness(
        self,
        workspace_id: UUID,
        payload: WorkspaceQuickActionRequest,
    ) -> WorkspaceQuickActionResponse:
        run = await ProductReadinessService(
            ProductReadinessRepository(self.session),
            settings=self.settings,
        ).run_readiness_check(workspace_id)
        return WorkspaceQuickActionResponse(
            workspace_id=workspace_id,
            action_type=normalize_action_type(payload.action_type),
            status=run.status.value if hasattr(run.status, "value") else str(run.status),
            summary=run.summary,
            created_artifact_ids_json={"productReadinessRunId": str(run.id)},
            result_json={
                "readinessLabel": run.readiness_label.value
                if hasattr(run.readiness_label, "value")
                else str(run.readiness_label),
                "readinessScore": str(run.readiness_score),
                "blockerCount": len(run.blockers_json),
                "warningCount": len(run.warnings_json),
            },
        )


def normalize_action_type(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def option_value(options: dict[str, Any], key: str, default: object) -> object:
    camel_key = "".join([key.split("_")[0], *[part.capitalize() for part in key.split("_")[1:]]])
    return options.get(key, options.get(camel_key, default))


def bounded_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)


def parse_date_option(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return date.fromisoformat(value)
