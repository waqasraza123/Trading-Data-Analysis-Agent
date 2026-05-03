from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from importlib import import_module
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.daily_workflows.models import (
    DailyWorkflowRun,
    DailyWorkflowRunStatus,
    DailyWorkflowStep,
    DailyWorkflowStepKey,
    DailyWorkflowStepStatus,
)
from app.modules.daily_workflows.repository import DailyWorkflowRepository
from app.modules.daily_workflows.schemas import DailyWorkflowOptions
from app.modules.market_memory.service import MarketMemoryService
from app.modules.market_scans.models import ScheduledScanMode
from app.modules.market_scans.scanner import MarketScanExecutor
from app.modules.market_scans.schemas import ScheduledScanConfigCreate
from app.modules.market_scans.service import MarketScanService
from app.modules.provider_health.models import ProviderHealthSnapshot
from app.modules.provider_health.service import ProviderHealthService
from app.modules.setup_context.service import SetupContextService
from app.modules.signal_digests.models import SignalDigestType
from app.modules.signal_digests.schemas import SignalDigestCreate, SignalDigestFilters
from app.modules.signal_digests.service import SignalDigestService
from app.modules.signal_priority.service import SignalPriorityService

DAILY_WORKFLOW_STEP_ORDER = [
    DailyWorkflowStepKey.PROVIDER_HEALTH_REFRESH,
    DailyWorkflowStepKey.GAP_RECOVERY_PREPARE,
    DailyWorkflowStepKey.SCHEDULED_SCAN_RUN,
    DailyWorkflowStepKey.SETUP_CONTEXT_GENERATE,
    DailyWorkflowStepKey.SIGNAL_PRIORITY_SCORE,
    DailyWorkflowStepKey.MARKET_MEMORY_REFRESH,
    DailyWorkflowStepKey.SIGNAL_DIGEST_GENERATE,
    DailyWorkflowStepKey.DAILY_BRIEF_GENERATE,
]


@dataclass
class WorkflowTarget:
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str


@dataclass
class DailyWorkflowExecutionState:
    snapshot_ids: list[str] = field(default_factory=list)
    recovery_plan_ids: list[str] = field(default_factory=list)
    provider_polling_request_ids: list[str] = field(default_factory=list)
    scan_run_ids: list[str] = field(default_factory=list)
    analysis_run_ids: list[str] = field(default_factory=list)
    signal_ids: list[str] = field(default_factory=list)
    setup_context_ids: list[str] = field(default_factory=list)
    priority_score_ids: list[str] = field(default_factory=list)
    market_memory_snapshot_ids: list[str] = field(default_factory=list)
    digest_run_ids: list[str] = field(default_factory=list)
    daily_brief_run_ids: list[str] = field(default_factory=list)
    targets: list[WorkflowTarget] = field(default_factory=list)

    def artifact_ids(self) -> dict[str, object]:
        return {
            "providerHealthSnapshotIds": self.snapshot_ids,
            "gapRecoveryPlanIds": self.recovery_plan_ids,
            "providerPollingRequestIds": self.provider_polling_request_ids,
            "scheduledScanRunIds": self.scan_run_ids,
            "analysisRunIds": self.analysis_run_ids,
            "signalIds": self.signal_ids,
            "setupContextIds": self.setup_context_ids,
            "signalPriorityScoreIds": self.priority_score_ids,
            "marketMemorySnapshotIds": self.market_memory_snapshot_ids,
            "signalDigestRunIds": self.digest_run_ids,
            "dailyBriefRunIds": self.daily_brief_run_ids,
        }


@dataclass(frozen=True)
class DailyWorkflowStepResult:
    status: DailyWorkflowStepStatus
    output_json: dict[str, object]
    skipped_reason: str | None = None


class DailyWorkflowRunner:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: DailyWorkflowRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or DailyWorkflowRepository(session)

    async def run(
        self,
        workflow_run: DailyWorkflowRun,
        options: DailyWorkflowOptions,
    ) -> DailyWorkflowRun:
        state = DailyWorkflowExecutionState()
        workflow_run.status = DailyWorkflowRunStatus.RUNNING.value
        workflow_run.started_at = workflow_run.started_at or utc_now()
        workflow_run.summary = "Daily workflow running"
        await self.repository.update_run(workflow_run)
        await self.session.commit()
        step_statuses: list[DailyWorkflowStepStatus] = []
        for step_key in DAILY_WORKFLOW_STEP_ORDER:
            step = await self.run_step(workflow_run, step_key, options, state)
            step_statuses.append(DailyWorkflowStepStatus(step.status))
        workflow_run.created_artifact_ids_json = state.artifact_ids()
        workflow_run.steps_json = await self.build_step_summaries(workflow_run.id)
        workflow_run.result_json = build_workflow_result(state)
        workflow_run.completed_at = utc_now()
        workflow_run.status = final_status(step_statuses)
        workflow_run.summary = build_workflow_summary(workflow_run.status, state)
        await self.repository.update_run(workflow_run)
        await self.session.commit()
        await self.session.refresh(workflow_run)
        return workflow_run

    async def run_step(
        self,
        workflow_run: DailyWorkflowRun,
        step_key: DailyWorkflowStepKey,
        options: DailyWorkflowOptions,
        state: DailyWorkflowExecutionState,
    ) -> DailyWorkflowStep:
        existing = await self.repository.get_step_by_key(workflow_run.id, step_key.value)
        if (
            existing is not None
            and existing.status == DailyWorkflowStepStatus.COMPLETED.value
            and not options.force
        ):
            return existing
        step = existing or await self.repository.create_step(
            DailyWorkflowStep(
                workspace_id=workflow_run.workspace_id,
                workflow_run_id=workflow_run.id,
                step_key=step_key.value,
                status=DailyWorkflowStepStatus.PENDING.value,
                input_json=step_input_json(workflow_run, options),
            )
        )
        step.status = DailyWorkflowStepStatus.RUNNING.value
        step.started_at = step.started_at or utc_now()
        step.completed_at = None
        step.error_message = None
        step.skipped_reason = None
        await self.repository.update_step(step)
        await self.session.commit()
        try:
            result = await self.execute_step(step_key, workflow_run, options, state)
            step.status = result.status.value
            step.output_json = result.output_json
            step.skipped_reason = result.skipped_reason
        except Exception as error:
            step.status = DailyWorkflowStepStatus.FAILED.value
            step.output_json = {"errorType": type(error).__name__}
            step.error_message = safe_error_message(error)
        step.completed_at = utc_now()
        await self.repository.update_step(step)
        await self.session.commit()
        return step

    async def execute_step(
        self,
        step_key: DailyWorkflowStepKey,
        workflow_run: DailyWorkflowRun,
        options: DailyWorkflowOptions,
        state: DailyWorkflowExecutionState,
    ) -> DailyWorkflowStepResult:
        handlers: dict[
            DailyWorkflowStepKey,
            Callable[
                [DailyWorkflowRun, DailyWorkflowOptions, DailyWorkflowExecutionState],
                Awaitable[DailyWorkflowStepResult],
            ],
        ] = {
            DailyWorkflowStepKey.PROVIDER_HEALTH_REFRESH: self.provider_health_refresh,
            DailyWorkflowStepKey.GAP_RECOVERY_PREPARE: self.gap_recovery_prepare,
            DailyWorkflowStepKey.SCHEDULED_SCAN_RUN: self.scheduled_scan_run,
            DailyWorkflowStepKey.SETUP_CONTEXT_GENERATE: self.setup_context_generate,
            DailyWorkflowStepKey.SIGNAL_PRIORITY_SCORE: self.signal_priority_score,
            DailyWorkflowStepKey.MARKET_MEMORY_REFRESH: self.market_memory_refresh,
            DailyWorkflowStepKey.SIGNAL_DIGEST_GENERATE: self.signal_digest_generate,
            DailyWorkflowStepKey.DAILY_BRIEF_GENERATE: self.daily_brief_generate,
        }
        return await handlers[step_key](workflow_run, options, state)

    async def provider_health_refresh(
        self,
        workflow_run: DailyWorkflowRun,
        options: DailyWorkflowOptions,
        state: DailyWorkflowExecutionState,
    ) -> DailyWorkflowStepResult:
        snapshots, skipped_count = await ProviderHealthService(
            self.session,
            self.settings,
        ).build_workspace_health(
            workspace_id=workflow_run.workspace_id,
            limit=self.settings.daily_workflow_max_symbols,
        )
        state.snapshot_ids = unique_strings(
            [*state.snapshot_ids, *[str(snapshot.id) for snapshot in snapshots]]
        )
        return DailyWorkflowStepResult(
            status=DailyWorkflowStepStatus.COMPLETED,
            output_json={
                "refreshedCount": len(snapshots),
                "skippedCount": skipped_count,
                "snapshotIds": [str(snapshot.id) for snapshot in snapshots],
            },
        )

    async def gap_recovery_prepare(
        self,
        workflow_run: DailyWorkflowRun,
        options: DailyWorkflowOptions,
        state: DailyWorkflowExecutionState,
    ) -> DailyWorkflowStepResult:
        if not options.prepare_gap_recovery:
            return skipped("gap_recovery_disabled")
        service = ProviderHealthService(self.session, self.settings)
        snapshots = await self.load_refreshed_snapshots(state.snapshot_ids)
        candidates = [
            snapshot
            for snapshot in snapshots
            if snapshot.symbol_id is not None
            and snapshot.timeframe is not None
            and snapshot.missing_candle_count > 0
        ][: self.settings.daily_workflow_max_symbols]
        create_requests = should_create_provider_polling_requests(options, self.settings)
        plan_ids: list[str] = []
        request_ids: list[str] = []
        skipped_count = 0
        for snapshot in candidates:
            try:
                response = await service.prepare_gap_recovery(
                    snapshot.id,
                    create_requests=create_requests,
                )
            except AppError:
                skipped_count += 1
                continue
            plan_ids.append(str(response.recovery_plan.id))
            if response.preparation is not None:
                request_ids.extend(
                    str(request.provider_polling_request_id)
                    for request in response.preparation.requests
                    if request.provider_polling_request_id is not None
                )
        state.recovery_plan_ids = unique_strings([*state.recovery_plan_ids, *plan_ids])
        state.provider_polling_request_ids = unique_strings(
            [*state.provider_polling_request_ids, *request_ids]
        )
        return DailyWorkflowStepResult(
            status=DailyWorkflowStepStatus.COMPLETED,
            output_json={
                "candidateSnapshotCount": len(candidates),
                "preparedPlanCount": len(set(plan_ids)),
                "createdProviderPollingRequestCount": len(set(request_ids)),
                "skippedCount": skipped_count,
                "providerPollingRequested": options.allow_provider_polling,
                "providerPollingEnabled": self.settings.daily_workflow_enable_provider_polling,
                "providerPollingCreated": create_requests,
                "recoveryPlanIds": unique_strings(plan_ids),
                "providerPollingRequestIds": unique_strings(request_ids),
            },
        )

    async def scheduled_scan_run(
        self,
        workflow_run: DailyWorkflowRun,
        options: DailyWorkflowOptions,
        state: DailyWorkflowExecutionState,
    ) -> DailyWorkflowStepResult:
        if not options.run_scan or workflow_run.workflow_type == "data_refresh_only":
            return skipped("scan_disabled")
        executor = MarketScanExecutor(self.session, settings=self.settings)
        if workflow_run.watchlist_id is not None:
            config = await self.repository.get_active_watchlist_scan_config(
                workflow_run.workspace_id,
                workflow_run.watchlist_id,
            )
            if config is None:
                config = await MarketScanService(self.session, self.settings).create_scan_config(
                    ScheduledScanConfigCreate(
                        workspace_id=workflow_run.workspace_id,
                        name="Daily workflow watchlist scan",
                        description="Workflow-owned deterministic watchlist scan config.",
                        watchlist_id=workflow_run.watchlist_id,
                        scan_mode=ScheduledScanMode.WATCHLIST,
                        lookback_minutes=self.settings.market_scan_default_lookback_minutes,
                        interval_seconds=self.settings.market_scan_default_interval_seconds,
                        include_partial_live_candle=False,
                        include_news_correlation=False,
                        include_ai_explanation=False,
                        include_reasoning=False,
                        include_action_plan=False,
                        metadata_json={"createdBy": "daily_workflow"},
                    )
                )
            runs = [await executor.run_scan_config(config.id, force=True)]
        else:
            runs = await executor.run_due_scan_configs(
                workspace_id=workflow_run.workspace_id,
                limit=min(self.settings.daily_workflow_max_scan_items, 500),
            )
        scan_run_ids = [str(run.id) for run in runs]
        analysis_run_ids = unique_strings(
            [str(analysis_run_id) for run in runs for analysis_run_id in run.analysis_run_ids_json]
        )
        signal_ids = unique_strings(
            [str(signal_id) for run in runs for signal_id in run.signal_ids_json]
        )
        state.scan_run_ids = unique_strings([*state.scan_run_ids, *scan_run_ids])
        state.analysis_run_ids = unique_strings([*state.analysis_run_ids, *analysis_run_ids])
        state.signal_ids = unique_strings([*state.signal_ids, *signal_ids])
        await self.collect_scan_targets(runs, state)
        return DailyWorkflowStepResult(
            status=DailyWorkflowStepStatus.COMPLETED if runs else DailyWorkflowStepStatus.SKIPPED,
            skipped_reason=None if runs else "no_due_or_configured_scans",
            output_json={
                "runCount": len(runs),
                "scanRunIds": scan_run_ids,
                "analysisRunIds": analysis_run_ids,
                "signalIds": signal_ids,
                "targetCount": len(state.targets),
            },
        )

    async def setup_context_generate(
        self,
        workflow_run: DailyWorkflowRun,
        options: DailyWorkflowOptions,
        state: DailyWorkflowExecutionState,
    ) -> DailyWorkflowStepResult:
        if not options.generate_setup_context:
            return skipped("setup_context_disabled")
        if not state.signal_ids:
            return skipped("no_signals_available")
        service = SetupContextService(self.session, self.settings)
        created_ids: list[str] = []
        skipped_count = 0
        for signal_id in state.signal_ids[: self.settings.daily_workflow_max_scan_items]:
            try:
                context = await service.build_for_signal(
                    UUID(signal_id),
                    force_recompute=options.force,
                )
            except AppError:
                skipped_count += 1
                continue
            created_ids.append(str(context.id))
        state.setup_context_ids = unique_strings([*state.setup_context_ids, *created_ids])
        return DailyWorkflowStepResult(
            status=DailyWorkflowStepStatus.COMPLETED,
            output_json={
                "generatedCount": len(set(created_ids)),
                "skippedCount": skipped_count,
                "setupContextIds": unique_strings(created_ids),
            },
        )

    async def signal_priority_score(
        self,
        workflow_run: DailyWorkflowRun,
        options: DailyWorkflowOptions,
        state: DailyWorkflowExecutionState,
    ) -> DailyWorkflowStepResult:
        if not options.score_priorities:
            return skipped("priority_scoring_disabled")
        service = SignalPriorityService(self.session, self.settings)
        score_ids: list[str] = []
        skipped_count = 0
        signal_ids = state.signal_ids[: self.settings.daily_workflow_max_scan_items]
        if not signal_ids:
            scores, skipped_recent = await service.score_workspace_recent_signals(
                workflow_run.workspace_id,
                limit=self.settings.daily_workflow_max_scan_items,
                force_recompute=options.force,
            )
            score_ids.extend(str(score.id) for score in scores)
            skipped_count += skipped_recent
        else:
            for signal_id in signal_ids:
                try:
                    score = await service.score_signal(
                        UUID(signal_id),
                        force_recompute=options.force,
                    )
                except AppError:
                    skipped_count += 1
                    continue
                score_ids.append(str(score.id))
        state.priority_score_ids = unique_strings([*state.priority_score_ids, *score_ids])
        return DailyWorkflowStepResult(
            status=DailyWorkflowStepStatus.COMPLETED,
            output_json={
                "scoredCount": len(set(score_ids)),
                "skippedCount": skipped_count,
                "priorityScoreIds": unique_strings(score_ids),
            },
        )

    async def market_memory_refresh(
        self,
        workflow_run: DailyWorkflowRun,
        options: DailyWorkflowOptions,
        state: DailyWorkflowExecutionState,
    ) -> DailyWorkflowStepResult:
        service = MarketMemoryService(self.session, self.settings)
        snapshot_ids: list[str] = []
        skipped_count = 0
        targets = unique_targets(state.targets)[: self.settings.daily_workflow_max_symbols]
        if not targets:
            snapshots, skipped_recent = await service.refresh_workspace_snapshots(
                workflow_run.workspace_id,
                limit=self.settings.daily_workflow_max_symbols,
            )
            snapshot_ids.extend(str(snapshot.id) for snapshot in snapshots)
            skipped_count += skipped_recent
        else:
            for target in targets:
                try:
                    snapshot = await service.build_state_snapshot(
                        workspace_id=workflow_run.workspace_id,
                        symbol_id=target.symbol_id,
                        source_id=target.source_id,
                        timeframe=target.timeframe,
                        force_recompute=options.force,
                    )
                except AppError:
                    skipped_count += 1
                    continue
                snapshot_ids.append(str(snapshot.id))
        state.market_memory_snapshot_ids = unique_strings(
            [*state.market_memory_snapshot_ids, *snapshot_ids]
        )
        return DailyWorkflowStepResult(
            status=DailyWorkflowStepStatus.COMPLETED,
            output_json={
                "refreshedCount": len(set(snapshot_ids)),
                "skippedCount": skipped_count,
                "marketMemorySnapshotIds": unique_strings(snapshot_ids),
            },
        )

    async def signal_digest_generate(
        self,
        workflow_run: DailyWorkflowRun,
        options: DailyWorkflowOptions,
        state: DailyWorkflowExecutionState,
    ) -> DailyWorkflowStepResult:
        if not options.generate_digest:
            return skipped("signal_digest_disabled")
        period_start, period_end = workflow_period(workflow_run)
        digest_type = (
            SignalDigestType.WATCHLIST
            if workflow_run.workflow_type == "watchlist_scan"
            else SignalDigestType.DAILY
        )
        digest = await SignalDigestService(self.session, self.settings).create_digest(
            SignalDigestCreate(
                workspace_id=workflow_run.workspace_id,
                digest_type=digest_type,
                period_start=period_start,
                period_end=period_end,
                timezone=self.settings.signal_digest_default_timezone,
                filters=SignalDigestFilters(watchlist_id=workflow_run.watchlist_id),
                max_items=min(
                    self.settings.signal_digest_max_items,
                    self.settings.daily_workflow_max_scan_items,
                ),
            )
        )
        state.digest_run_ids = unique_strings([*state.digest_run_ids, str(digest.id)])
        return DailyWorkflowStepResult(
            status=DailyWorkflowStepStatus.COMPLETED,
            output_json={
                "digestRunId": str(digest.id),
                "digestType": digest.digest_type,
                "status": digest.status,
                "title": digest.title,
                "briefHref": f"/brief?workspaceId={workflow_run.workspace_id}",
            },
        )

    async def daily_brief_generate(
        self,
        workflow_run: DailyWorkflowRun,
        options: DailyWorkflowOptions,
        state: DailyWorkflowExecutionState,
    ) -> DailyWorkflowStepResult:
        if not options.generate_brief:
            return skipped("daily_brief_disabled")
        try:
            service_module = import_module("app.modules.daily_briefs.service")
            schemas_module = import_module("app.modules.daily_briefs.schemas")
            models_module = import_module("app.modules.daily_briefs.models")
        except ImportError:
            return DailyWorkflowStepResult(
                status=DailyWorkflowStepStatus.SKIPPED,
                skipped_reason="backend_daily_brief_service_unavailable",
                output_json={
                    "briefHref": f"/brief?workspaceId={workflow_run.workspace_id}",
                    "digestRunIds": state.digest_run_ids,
                },
            )
        period_start, period_end = workflow_period(workflow_run)
        brief_type = (
            models_module.DailyBriefType.WATCHLIST
            if workflow_run.watchlist_id is not None
            else models_module.DailyBriefType.DAILY
        )
        brief = await service_module.DailyBriefService(self.session, self.settings).create_brief(
            schemas_module.DailyBriefCreate(
                workspace_id=workflow_run.workspace_id,
                brief_type=brief_type,
                period_start=period_start,
                period_end=period_end,
                timezone=getattr(self.settings, "daily_brief_default_timezone", "UTC"),
                watchlist_id=workflow_run.watchlist_id,
                filters=schemas_module.DailyBriefFilters(
                    preference_profile_id=workflow_run.preference_profile_id
                ),
            )
        )
        state.daily_brief_run_ids = unique_strings([*state.daily_brief_run_ids, str(brief.id)])
        return DailyWorkflowStepResult(
            status=DailyWorkflowStepStatus.COMPLETED,
            output_json={
                "dailyBriefRunId": str(brief.id),
                "status": brief.status,
                "briefType": brief.brief_type,
                "briefHref": f"/brief?workspaceId={workflow_run.workspace_id}",
                "digestRunIds": state.digest_run_ids,
            },
        )

    async def load_refreshed_snapshots(
        self,
        snapshot_ids: list[str],
    ) -> list[ProviderHealthSnapshot]:
        snapshots: list[ProviderHealthSnapshot] = []
        service = ProviderHealthService(self.session, self.settings)
        for snapshot_id in snapshot_ids[: self.settings.daily_workflow_max_symbols]:
            snapshot = await service.repository.get_snapshot(UUID(snapshot_id))
            if snapshot is not None:
                snapshots.append(snapshot)
        return snapshots

    async def collect_scan_targets(
        self,
        runs: list[Any],
        state: DailyWorkflowExecutionState,
    ) -> None:
        executor = MarketScanExecutor(self.session, settings=self.settings)
        for run in runs:
            items = await executor.repository.list_scan_run_items(
                scan_run_id=run.id,
                limit=self.settings.daily_workflow_max_scan_items,
                offset=0,
            )
            for item in items:
                state.targets.append(
                    WorkflowTarget(
                        symbol_id=item.symbol_id,
                        source_id=item.source_id,
                        timeframe=item.timeframe,
                    )
                )

    async def build_step_summaries(self, workflow_run_id: UUID) -> list[dict[str, object]]:
        steps = await self.repository.list_steps(workflow_run_id)
        return [
            {
                "id": str(step.id),
                "stepKey": step.step_key,
                "status": step.status,
                "skippedReason": step.skipped_reason,
                "errorMessage": step.error_message,
                "startedAt": iso_or_none(step.started_at),
                "completedAt": iso_or_none(step.completed_at),
            }
            for step in steps
        ]


def should_create_provider_polling_requests(
    options: DailyWorkflowOptions,
    settings: Settings,
) -> bool:
    return bool(options.allow_provider_polling and settings.daily_workflow_enable_provider_polling)


def step_input_json(
    workflow_run: DailyWorkflowRun,
    options: DailyWorkflowOptions,
) -> dict[str, object]:
    return {
        "workspaceId": str(workflow_run.workspace_id),
        "workflowType": workflow_run.workflow_type,
        "watchlistId": str(workflow_run.watchlist_id) if workflow_run.watchlist_id else None,
        "preferenceProfileId": (
            str(workflow_run.preference_profile_id) if workflow_run.preference_profile_id else None
        ),
        "periodStart": iso_or_none(workflow_run.period_start),
        "periodEnd": iso_or_none(workflow_run.period_end),
        "options": options.model_dump(mode="json", by_alias=True),
    }


def skipped(reason: str) -> DailyWorkflowStepResult:
    return DailyWorkflowStepResult(
        status=DailyWorkflowStepStatus.SKIPPED,
        output_json={},
        skipped_reason=reason,
    )


def workflow_period(workflow_run: DailyWorkflowRun) -> tuple[datetime, datetime]:
    if workflow_run.period_start is not None and workflow_run.period_end is not None:
        return workflow_run.period_start, workflow_run.period_end
    now = utc_now()
    return (
        datetime.combine(now.date(), time.min, tzinfo=UTC),
        datetime.combine(now.date(), time.max, tzinfo=UTC),
    )


def build_workflow_result(state: DailyWorkflowExecutionState) -> dict[str, object]:
    return {
        "scanRunIds": state.scan_run_ids,
        "analysisRunIds": state.analysis_run_ids,
        "signalIds": state.signal_ids,
        "setupContextIds": state.setup_context_ids,
        "signalPriorityScoreIds": state.priority_score_ids,
        "marketMemorySnapshotIds": state.market_memory_snapshot_ids,
        "signalDigestRunIds": state.digest_run_ids,
        "dailyBriefRunIds": state.daily_brief_run_ids,
        "providerHealthSnapshotIds": state.snapshot_ids,
        "gapRecoveryPlanIds": state.recovery_plan_ids,
        "providerPollingRequestIds": state.provider_polling_request_ids,
    }


def build_workflow_summary(status: str, state: DailyWorkflowExecutionState) -> str:
    if status == DailyWorkflowRunStatus.COMPLETED.value:
        return (
            f"Daily workflow completed with {len(state.signal_ids)} signal records, "
            f"{len(state.setup_context_ids)} setup contexts, and "
            f"{len(state.digest_run_ids)} digests."
        )
    if status == DailyWorkflowRunStatus.COMPLETED_WITH_WARNINGS.value:
        return (
            f"Daily workflow completed with warnings; {len(state.signal_ids)} signal records and "
            f"{len(state.recovery_plan_ids)} recovery plans were recorded."
        )
    return "Daily workflow failed before all deterministic steps completed."


def final_status(step_statuses: list[DailyWorkflowStepStatus]) -> str:
    if any(status == DailyWorkflowStepStatus.FAILED for status in step_statuses):
        return DailyWorkflowRunStatus.COMPLETED_WITH_WARNINGS.value
    if any(status == DailyWorkflowStepStatus.SKIPPED for status in step_statuses):
        return DailyWorkflowRunStatus.COMPLETED_WITH_WARNINGS.value
    return DailyWorkflowRunStatus.COMPLETED.value


def safe_error_message(error: Exception) -> str:
    if isinstance(error, AppError):
        return error.message[:1000]
    return type(error).__name__


def unique_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def unique_targets(targets: list[WorkflowTarget]) -> list[WorkflowTarget]:
    unique: dict[tuple[UUID, UUID | None, str], WorkflowTarget] = {}
    for target in targets:
        unique.setdefault((target.symbol_id, target.source_id, target.timeframe), target)
    return list(unique.values())


def iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
