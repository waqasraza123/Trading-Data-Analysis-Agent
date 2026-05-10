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
from app.modules.daily_routines.models import (
    DailyRoutineRun,
    DailyRoutineRunStatus,
    DailyRoutineRunStep,
    DailyRoutineRunStepStatus,
    DailyRoutineStepKey,
    DailyRoutineTemplate,
)
from app.modules.daily_routines.repository import DailyRoutineRepository
from app.modules.daily_routines.schemas import DailyRoutineRunRequest
from app.modules.daily_workflows.models import DailyWorkflowType
from app.modules.daily_workflows.repository import DailyWorkflowRepository
from app.modules.daily_workflows.schemas import DailyWorkflowOptions, DailyWorkflowRunRequest
from app.modules.daily_workflows.service import DailyWorkflowService
from app.modules.market_memory.service import MarketMemoryService
from app.modules.market_scans.scanner import MarketScanExecutor
from app.modules.provider_health.models import ProviderHealthSnapshot
from app.modules.provider_health.service import ProviderHealthService
from app.modules.setup_context.service import SetupContextService
from app.modules.signal_digests.models import SignalDigestType
from app.modules.signal_digests.schemas import SignalDigestCreate, SignalDigestFilters
from app.modules.signal_digests.service import SignalDigestService
from app.modules.signal_priority.service import SignalPriorityService


@dataclass
class DailyRoutineExecutionState:
    provider_health_snapshot_ids: list[str] = field(default_factory=list)
    gap_recovery_plan_ids: list[str] = field(default_factory=list)
    provider_polling_request_ids: list[str] = field(default_factory=list)
    daily_workflow_run_ids: list[str] = field(default_factory=list)
    scheduled_scan_run_ids: list[str] = field(default_factory=list)
    analysis_run_ids: list[str] = field(default_factory=list)
    signal_ids: list[str] = field(default_factory=list)
    setup_context_ids: list[str] = field(default_factory=list)
    signal_priority_score_ids: list[str] = field(default_factory=list)
    market_memory_snapshot_ids: list[str] = field(default_factory=list)
    signal_digest_run_ids: list[str] = field(default_factory=list)
    daily_brief_run_ids: list[str] = field(default_factory=list)
    notification_event_ids: list[str] = field(default_factory=list)

    def artifact_ids(self) -> dict[str, object]:
        return {
            "providerHealthSnapshotIds": self.provider_health_snapshot_ids,
            "gapRecoveryPlanIds": self.gap_recovery_plan_ids,
            "providerPollingRequestIds": self.provider_polling_request_ids,
            "dailyWorkflowRunIds": self.daily_workflow_run_ids,
            "scheduledScanRunIds": self.scheduled_scan_run_ids,
            "analysisRunIds": self.analysis_run_ids,
            "signalIds": self.signal_ids,
            "setupContextIds": self.setup_context_ids,
            "signalPriorityScoreIds": self.signal_priority_score_ids,
            "marketMemorySnapshotIds": self.market_memory_snapshot_ids,
            "signalDigestRunIds": self.signal_digest_run_ids,
            "dailyBriefRunIds": self.daily_brief_run_ids,
            "notificationEventIds": self.notification_event_ids,
        }


@dataclass(frozen=True)
class DailyRoutineStepDefinition:
    step_key: str
    required: bool
    input_json: dict[str, object]


@dataclass(frozen=True)
class DailyRoutineStepResult:
    status: DailyRoutineRunStepStatus
    output_json: dict[str, object]
    skipped_reason: str | None = None


StepHandler = Callable[
    [
        DailyRoutineRun,
        DailyRoutineStepDefinition,
        DailyRoutineRunRequest,
        DailyRoutineExecutionState,
    ],
    Awaitable[DailyRoutineStepResult],
]


class DailyRoutineRunner:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: DailyRoutineRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or DailyRoutineRepository(session)

    async def run(
        self,
        routine_run: DailyRoutineRun,
        template: DailyRoutineTemplate,
        payload: DailyRoutineRunRequest,
    ) -> DailyRoutineRun:
        state = DailyRoutineExecutionState()
        definitions = parse_step_definitions(template.steps_json)
        routine_run.status = DailyRoutineRunStatus.RUNNING.value
        routine_run.started_at = routine_run.started_at or utc_now()
        routine_run.summary = "Daily routine running"
        await self.repository.update_run(routine_run)
        await self.session.commit()

        step_statuses: list[tuple[DailyRoutineRunStepStatus, bool]] = []
        for definition in definitions[: self.settings.daily_routine_max_steps]:
            step = await self.run_step(routine_run, definition, payload, state)
            step_statuses.append((DailyRoutineRunStepStatus(step.status), definition.required))

        routine_run.created_artifact_ids_json = state.artifact_ids()
        routine_run.step_results_json = await self.build_step_summaries(routine_run.id)
        routine_run.completed_at = utc_now()
        routine_run.status = final_status(step_statuses)
        routine_run.summary = build_routine_summary(
            status=routine_run.status,
            template_key=template.key,
            state=state,
            step_count=len(step_statuses),
        )
        if routine_run.status == DailyRoutineRunStatus.FAILED.value:
            routine_run.error_message = "A required daily routine step failed."
        await self.repository.update_run(routine_run)
        await self.session.commit()
        await self.session.refresh(routine_run)
        return routine_run

    async def run_step(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineRunStep:
        step = await self.repository.create_step(
            DailyRoutineRunStep(
                workspace_id=routine_run.workspace_id,
                routine_run_id=routine_run.id,
                step_key=definition.step_key,
                status=DailyRoutineRunStepStatus.PENDING.value,
                input_json=step_input_json(routine_run, definition, payload),
            )
        )
        step.status = DailyRoutineRunStepStatus.RUNNING.value
        step.started_at = utc_now()
        await self.repository.update_step(step)
        await self.session.commit()
        try:
            result = await self.execute_step(definition, routine_run, payload, state)
            step.status = result.status.value
            step.output_json = result.output_json
            step.skipped_reason = result.skipped_reason
        except Exception as error:
            step.status = DailyRoutineRunStepStatus.FAILED.value
            step.output_json = {"errorType": type(error).__name__, "required": definition.required}
            step.error_message = safe_error_message(error)
        step.completed_at = utc_now()
        await self.repository.update_step(step)
        await self.session.commit()
        return step

    async def execute_step(
        self,
        definition: DailyRoutineStepDefinition,
        routine_run: DailyRoutineRun,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        try:
            step_key = DailyRoutineStepKey(definition.step_key)
        except ValueError:
            return skipped("routine_step_unrecognized")
        handlers: dict[DailyRoutineStepKey, StepHandler] = {
            DailyRoutineStepKey.PROVIDER_HEALTH_REFRESH: self.provider_health_refresh,
            DailyRoutineStepKey.GAP_RECOVERY_PREPARE: self.gap_recovery_prepare,
            DailyRoutineStepKey.DAILY_WORKFLOW_RUN: self.daily_workflow_run,
            DailyRoutineStepKey.SCHEDULED_SCAN_RUN: self.scheduled_scan_run,
            DailyRoutineStepKey.SETUP_CONTEXT_GENERATE: self.setup_context_generate,
            DailyRoutineStepKey.SIGNAL_PRIORITY_SCORE: self.signal_priority_score,
            DailyRoutineStepKey.MARKET_MEMORY_REFRESH: self.market_memory_refresh,
            DailyRoutineStepKey.DIGEST_GENERATE: self.digest_generate,
            DailyRoutineStepKey.BRIEF_GENERATE: self.brief_generate,
            DailyRoutineStepKey.OUTCOME_REVIEW_COLLECT: self.outcome_review_collect,
            DailyRoutineStepKey.QUALITY_SUMMARY_COLLECT: self.quality_summary_collect,
            DailyRoutineStepKey.JOURNAL_FOLLOW_UP_COLLECT: self.journal_follow_up_collect,
            DailyRoutineStepKey.NOTIFICATION_EVENT_CREATE: self.notification_event_create,
        }
        return await handlers[step_key](routine_run, definition, payload, state)

    async def provider_health_refresh(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        snapshots, skipped_count = await ProviderHealthService(
            self.session,
            self.settings,
        ).build_workspace_health(
            workspace_id=routine_run.workspace_id,
            limit=self.settings.daily_workflow_max_symbols,
        )
        snapshot_ids = [str(snapshot.id) for snapshot in snapshots]
        state.provider_health_snapshot_ids = unique_strings(
            [*state.provider_health_snapshot_ids, *snapshot_ids]
        )
        return completed(
            {
                "refreshedCount": len(snapshot_ids),
                "skippedCount": skipped_count,
                "snapshotIds": snapshot_ids,
            }
        )

    async def gap_recovery_prepare(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        service = ProviderHealthService(self.session, self.settings)
        snapshots = await self.load_snapshots(state.provider_health_snapshot_ids)
        candidates = [
            snapshot
            for snapshot in snapshots
            if snapshot.symbol_id is not None
            and snapshot.timeframe is not None
            and snapshot.missing_candle_count > 0
        ][: self.settings.daily_workflow_max_symbols]
        create_requests = bool(
            payload.allow_provider_polling and self.settings.daily_workflow_enable_provider_polling
        )
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
        state.gap_recovery_plan_ids = unique_strings([*state.gap_recovery_plan_ids, *plan_ids])
        state.provider_polling_request_ids = unique_strings(
            [*state.provider_polling_request_ids, *request_ids]
        )
        return completed(
            {
                "candidateSnapshotCount": len(candidates),
                "preparedPlanCount": len(set(plan_ids)),
                "createdProviderPollingRequestCount": len(set(request_ids)),
                "skippedCount": skipped_count,
                "providerPollingCreated": create_requests,
                "recoveryPlanIds": unique_strings(plan_ids),
                "providerPollingRequestIds": unique_strings(request_ids),
            }
        )

    async def daily_workflow_run(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        workflow = await DailyWorkflowService(self.session, self.settings).run_workflow(
            DailyWorkflowRunRequest(
                workspace_id=routine_run.workspace_id,
                workflow_type=workflow_type_for_input(payload, definition),
                watchlist_id=payload.watchlist_id,
                preference_profile_id=payload.preference_profile_id,
                period_start=payload.period_start,
                period_end=payload.period_end,
                options=DailyWorkflowOptions(
                    prepare_gap_recovery=True,
                    allow_provider_polling=payload.allow_provider_polling,
                    run_scan=True,
                    generate_setup_context=True,
                    score_priorities=True,
                    generate_digest=True,
                    generate_brief=True,
                    force=payload.force,
                ),
                filters_json={"source": "daily_routine", "routineRunId": str(routine_run.id)},
            )
        )
        merge_daily_workflow_artifacts(workflow.created_artifact_ids_json, state)
        state.daily_workflow_run_ids = unique_strings(
            [*state.daily_workflow_run_ids, str(workflow.id)]
        )
        return completed(
            {
                "dailyWorkflowRunId": str(workflow.id),
                "status": workflow.status,
                "summary": workflow.summary,
                "createdArtifactIds": workflow.created_artifact_ids_json,
            }
        )

    async def scheduled_scan_run(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        executor = MarketScanExecutor(self.session, settings=self.settings)
        scan_config_id = string_or_none(definition.input_json.get("scanConfigId"))
        if scan_config_id is not None:
            runs = [await executor.run_scan_config(UUID(scan_config_id), force=True)]
        elif payload.watchlist_id is not None:
            config = await DailyWorkflowRepository(self.session).get_active_watchlist_scan_config(
                routine_run.workspace_id,
                payload.watchlist_id,
            )
            if config is None:
                return skipped("no_active_watchlist_scan_config")
            runs = [await executor.run_scan_config(config.id, force=True)]
        else:
            runs = await executor.run_due_scan_configs(
                workspace_id=routine_run.workspace_id,
                limit=min(self.settings.daily_workflow_max_scan_items, 500),
            )
        scan_run_ids = [str(run.id) for run in runs]
        analysis_run_ids = unique_strings(
            [str(analysis_run_id) for run in runs for analysis_run_id in run.analysis_run_ids_json]
        )
        signal_ids = unique_strings(
            [str(signal_id) for run in runs for signal_id in run.signal_ids_json]
        )
        state.scheduled_scan_run_ids = unique_strings(
            [*state.scheduled_scan_run_ids, *scan_run_ids]
        )
        state.analysis_run_ids = unique_strings([*state.analysis_run_ids, *analysis_run_ids])
        state.signal_ids = unique_strings([*state.signal_ids, *signal_ids])
        if not runs:
            return DailyRoutineStepResult(
                status=DailyRoutineRunStepStatus.SKIPPED,
                skipped_reason="no_due_or_configured_scans",
                output_json={"runCount": 0},
            )
        return completed(
            {
                "runCount": len(runs),
                "scanRunIds": scan_run_ids,
                "analysisRunIds": analysis_run_ids,
                "signalIds": signal_ids,
            }
        )

    async def setup_context_generate(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        if not state.signal_ids:
            return skipped("no_signals_available")
        service = SetupContextService(self.session, self.settings)
        created_ids: list[str] = []
        skipped_count = 0
        for signal_id in state.signal_ids[: self.settings.daily_workflow_max_scan_items]:
            try:
                context = await service.build_for_signal(
                    UUID(signal_id),
                    force_recompute=payload.force,
                )
            except AppError:
                skipped_count += 1
                continue
            created_ids.append(str(context.id))
        state.setup_context_ids = unique_strings([*state.setup_context_ids, *created_ids])
        return completed(
            {
                "generatedCount": len(set(created_ids)),
                "skippedCount": skipped_count,
                "setupContextIds": unique_strings(created_ids),
            }
        )

    async def signal_priority_score(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        service = SignalPriorityService(self.session, self.settings)
        score_ids: list[str] = []
        skipped_count = 0
        if state.signal_ids:
            for signal_id in state.signal_ids[: self.settings.daily_workflow_max_scan_items]:
                try:
                    score = await service.score_signal(
                        UUID(signal_id),
                        force_recompute=payload.force,
                    )
                except AppError:
                    skipped_count += 1
                    continue
                score_ids.append(str(score.id))
        else:
            scores, skipped_recent = await service.score_workspace_recent_signals(
                routine_run.workspace_id,
                limit=self.settings.daily_workflow_max_scan_items,
                force_recompute=payload.force,
            )
            score_ids.extend(str(score.id) for score in scores)
            skipped_count += skipped_recent
        state.signal_priority_score_ids = unique_strings(
            [*state.signal_priority_score_ids, *score_ids]
        )
        return completed(
            {
                "scoredCount": len(set(score_ids)),
                "skippedCount": skipped_count,
                "priorityScoreIds": unique_strings(score_ids),
            }
        )

    async def market_memory_refresh(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        snapshots, skipped_count = await MarketMemoryService(
            self.session,
            self.settings,
        ).refresh_workspace_snapshots(
            routine_run.workspace_id,
            limit=self.settings.daily_workflow_max_symbols,
        )
        snapshot_ids = [str(snapshot.id) for snapshot in snapshots]
        state.market_memory_snapshot_ids = unique_strings(
            [*state.market_memory_snapshot_ids, *snapshot_ids]
        )
        return completed(
            {
                "refreshedCount": len(set(snapshot_ids)),
                "skippedCount": skipped_count,
                "marketMemorySnapshotIds": unique_strings(snapshot_ids),
            }
        )

    async def digest_generate(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        period_start, period_end = routine_period(payload)
        digest_type = SignalDigestType(
            string_or_none(definition.input_json.get("digestType")) or "daily"
        )
        digest = await SignalDigestService(self.session, self.settings).create_digest(
            SignalDigestCreate(
                workspace_id=routine_run.workspace_id,
                digest_type=digest_type,
                period_start=period_start,
                period_end=period_end,
                timezone=self.settings.signal_digest_default_timezone,
                filters=SignalDigestFilters(watchlist_id=payload.watchlist_id),
                max_items=min(
                    self.settings.signal_digest_max_items,
                    self.settings.daily_workflow_max_scan_items,
                ),
            )
        )
        state.signal_digest_run_ids = unique_strings([*state.signal_digest_run_ids, str(digest.id)])
        return completed(
            {
                "digestRunId": str(digest.id),
                "digestType": digest.digest_type,
                "status": digest.status,
                "title": digest.title,
            }
        )

    async def brief_generate(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        try:
            service_module = import_module("app.modules.daily_briefs.service")
            schemas_module = import_module("app.modules.daily_briefs.schemas")
            models_module = import_module("app.modules.daily_briefs.models")
        except ImportError:
            return skipped("backend_daily_brief_service_unavailable")
        period_start, period_end = routine_period(payload)
        requested_type = string_or_none(definition.input_json.get("briefType"))
        brief_type = models_module.DailyBriefType(
            requested_type or ("watchlist" if payload.watchlist_id is not None else "daily")
        )
        create_payload = schemas_module.DailyBriefCreate(
            workspace_id=routine_run.workspace_id,
            brief_type=brief_type,
            period_start=period_start,
            period_end=period_end,
            timezone=self.settings.daily_brief_default_timezone,
            watchlist_id=payload.watchlist_id,
            filters=schemas_module.DailyBriefFilters(
                preference_profile_id=payload.preference_profile_id
            ),
        )
        session_label = string_or_none(definition.input_json.get("sessionLabel"))
        brief = await service_module.DailyBriefService(self.session, self.settings).create_brief(
            create_payload,
            session_label=session_label,
        )
        state.daily_brief_run_ids = unique_strings([*state.daily_brief_run_ids, str(brief.id)])
        return completed(
            {
                "dailyBriefRunId": str(brief.id),
                "briefType": brief.brief_type,
                "status": brief.status,
                "digestRunIds": state.signal_digest_run_ids,
            }
        )

    async def outcome_review_collect(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        period_start, period_end = routine_period(payload)
        counts = await self.repository.count_recent_outcomes(
            routine_run.workspace_id,
            period_start,
            period_end,
        )
        return completed(
            {
                "outcomeCountsByLabel": counts,
                "totalOutcomeCount": sum(counts.values()),
                "collectOnly": True,
            }
        )

    async def quality_summary_collect(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        period_start, period_end = routine_period(payload)
        counts = await self.repository.count_recent_quality_runs(
            routine_run.workspace_id,
            period_start,
            period_end,
        )
        return completed(
            {
                "qualityCountsByLabel": counts,
                "totalQualityRunCount": sum(counts.values()),
                "collectOnly": True,
            }
        )

    async def journal_follow_up_collect(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        period_start, period_end = routine_period(payload)
        counts = await self.repository.count_journal_follow_up(
            routine_run.workspace_id,
            period_start,
            period_end,
        )
        return completed({**counts, "collectOnly": True})

    async def notification_event_create(
        self,
        routine_run: DailyRoutineRun,
        definition: DailyRoutineStepDefinition,
        payload: DailyRoutineRunRequest,
        state: DailyRoutineExecutionState,
    ) -> DailyRoutineStepResult:
        explicitly_enabled = bool(
            payload.enable_notifications or definition.input_json.get("enableNotifications")
        )
        if not explicitly_enabled:
            return skipped("notification_event_not_explicitly_enabled")
        if not self.settings.daily_routine_enable_notifications:
            return skipped("daily_routine_notifications_disabled")
        try:
            models_module = import_module("app.modules.notifications.models")
            schemas_module = import_module("app.modules.notifications.schemas")
            service_module = import_module("app.modules.notifications.service")
        except ImportError:
            return skipped("notification_module_unavailable")
        event = await service_module.NotificationService(
            self.session,
            self.settings,
        ).create_notification_event(
            schemas_module.NotificationEventCreate(
                workspace_id=routine_run.workspace_id,
                event_type=models_module.BackendNotificationEventType.DIGEST_CREATED,
                source_type="daily_routine_run",
                source_id=routine_run.id,
                severity=models_module.NotificationEventSeverity.INFO,
                title="Daily routine completed",
                summary="A deterministic daily routine run created an in-app event.",
                payload_json={
                    "routineRunId": str(routine_run.id),
                    "artifactIds": state.artifact_ids(),
                    "noBrokerExecution": True,
                    "noAutoTrading": True,
                    "noExternalDelivery": True,
                },
                dedupe_key=f"daily_routine:{routine_run.id}",
            )
        )
        state.notification_event_ids = unique_strings(
            [*state.notification_event_ids, str(event.id)]
        )
        return completed({"notificationEventId": str(event.id), "status": event.status})

    async def load_snapshots(self, snapshot_ids: list[str]) -> list[ProviderHealthSnapshot]:
        service = ProviderHealthService(self.session, self.settings)
        snapshots: list[ProviderHealthSnapshot] = []
        for snapshot_id in snapshot_ids[: self.settings.daily_workflow_max_symbols]:
            snapshot = await service.repository.get_snapshot(UUID(snapshot_id))
            if snapshot is not None:
                snapshots.append(snapshot)
        return snapshots

    async def build_step_summaries(self, routine_run_id: UUID) -> list[dict[str, object]]:
        steps = await self.repository.list_steps(routine_run_id)
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


def parse_step_definitions(steps_json: list[dict[str, Any]]) -> list[DailyRoutineStepDefinition]:
    definitions: list[DailyRoutineStepDefinition] = []
    for item in steps_json:
        step_key = string_or_none(item.get("stepKey") or item.get("step_key"))
        if step_key is None:
            continue
        input_json = item.get("inputJson") or item.get("input_json") or {}
        definitions.append(
            DailyRoutineStepDefinition(
                step_key=step_key,
                required=bool(item.get("required", False)),
                input_json=input_json if isinstance(input_json, dict) else {},
            )
        )
    return definitions


def step_input_json(
    routine_run: DailyRoutineRun,
    definition: DailyRoutineStepDefinition,
    payload: DailyRoutineRunRequest,
) -> dict[str, object]:
    return {
        "workspaceId": str(routine_run.workspace_id),
        "routineRunId": str(routine_run.id),
        "templateId": str(routine_run.template_id),
        "stepKey": definition.step_key,
        "required": definition.required,
        "inputJson": definition.input_json,
        "requestInput": payload.model_dump(mode="json", by_alias=True),
    }


def completed(output_json: dict[str, object]) -> DailyRoutineStepResult:
    return DailyRoutineStepResult(
        status=DailyRoutineRunStepStatus.COMPLETED,
        output_json=output_json,
    )


def skipped(reason: str) -> DailyRoutineStepResult:
    return DailyRoutineStepResult(
        status=DailyRoutineRunStepStatus.SKIPPED,
        output_json={},
        skipped_reason=reason,
    )


def routine_period(payload: DailyRoutineRunRequest) -> tuple[datetime, datetime]:
    if payload.period_start is not None and payload.period_end is not None:
        return payload.period_start, payload.period_end
    now = utc_now()
    return (
        datetime.combine(now.date(), time.min, tzinfo=UTC),
        datetime.combine(now.date(), time.max, tzinfo=UTC),
    )


def workflow_type_for_input(
    payload: DailyRoutineRunRequest,
    definition: DailyRoutineStepDefinition,
) -> DailyWorkflowType:
    requested_type = string_or_none(definition.input_json.get("workflowType"))
    if requested_type is not None:
        return DailyWorkflowType(requested_type)
    if payload.watchlist_id is not None:
        return DailyWorkflowType.WATCHLIST_SCAN
    return DailyWorkflowType.DAILY_SCAN


def merge_daily_workflow_artifacts(
    artifact_ids: dict[str, object],
    state: DailyRoutineExecutionState,
) -> None:
    state.provider_health_snapshot_ids = unique_strings(
        [
            *state.provider_health_snapshot_ids,
            *read_string_list(artifact_ids.get("providerHealthSnapshotIds")),
        ]
    )
    state.gap_recovery_plan_ids = unique_strings(
        [*state.gap_recovery_plan_ids, *read_string_list(artifact_ids.get("gapRecoveryPlanIds"))]
    )
    state.provider_polling_request_ids = unique_strings(
        [
            *state.provider_polling_request_ids,
            *read_string_list(artifact_ids.get("providerPollingRequestIds")),
        ]
    )
    state.scheduled_scan_run_ids = unique_strings(
        [*state.scheduled_scan_run_ids, *read_string_list(artifact_ids.get("scheduledScanRunIds"))]
    )
    state.analysis_run_ids = unique_strings(
        [*state.analysis_run_ids, *read_string_list(artifact_ids.get("analysisRunIds"))]
    )
    state.signal_ids = unique_strings(
        [*state.signal_ids, *read_string_list(artifact_ids.get("signalIds"))]
    )
    state.setup_context_ids = unique_strings(
        [*state.setup_context_ids, *read_string_list(artifact_ids.get("setupContextIds"))]
    )
    state.signal_priority_score_ids = unique_strings(
        [
            *state.signal_priority_score_ids,
            *read_string_list(artifact_ids.get("signalPriorityScoreIds")),
        ]
    )
    state.market_memory_snapshot_ids = unique_strings(
        [
            *state.market_memory_snapshot_ids,
            *read_string_list(artifact_ids.get("marketMemorySnapshotIds")),
        ]
    )
    state.signal_digest_run_ids = unique_strings(
        [*state.signal_digest_run_ids, *read_string_list(artifact_ids.get("signalDigestRunIds"))]
    )
    state.daily_brief_run_ids = unique_strings(
        [*state.daily_brief_run_ids, *read_string_list(artifact_ids.get("dailyBriefRunIds"))]
    )


def final_status(step_statuses: list[tuple[DailyRoutineRunStepStatus, bool]]) -> str:
    if any(
        status == DailyRoutineRunStepStatus.FAILED and required
        for status, required in step_statuses
    ):
        return DailyRoutineRunStatus.FAILED.value
    warning_statuses = {DailyRoutineRunStepStatus.FAILED, DailyRoutineRunStepStatus.SKIPPED}
    if any(status in warning_statuses for status, _ in step_statuses):
        return DailyRoutineRunStatus.COMPLETED_WITH_WARNINGS.value
    return DailyRoutineRunStatus.COMPLETED.value


def build_routine_summary(
    *,
    status: str,
    template_key: str,
    state: DailyRoutineExecutionState,
    step_count: int,
) -> str:
    if status == DailyRoutineRunStatus.FAILED.value:
        return f"Daily routine {template_key} failed after {step_count} bounded steps."
    if status == DailyRoutineRunStatus.COMPLETED_WITH_WARNINGS.value:
        return (
            f"Daily routine {template_key} completed with warnings across {step_count} steps; "
            f"{len(state.signal_ids)} signals and "
            f"{len(state.signal_digest_run_ids)} digests were recorded."
        )
    return (
        f"Daily routine {template_key} completed across {step_count} deterministic steps; "
        f"{len(state.signal_ids)} signals and "
        f"{len(state.daily_brief_run_ids)} briefs were recorded."
    )


def safe_error_message(error: Exception) -> str:
    if isinstance(error, AppError):
        return error.message[:1000]
    return type(error).__name__


def string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def read_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def unique_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
