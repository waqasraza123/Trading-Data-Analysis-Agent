from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.action_plans.models import ReasoningActionItem
from app.modules.daily_briefs.models import DailyBriefRun
from app.modules.daily_workflows.models import DailyWorkflowRun
from app.modules.data_quality.models import DataQualityFinding
from app.modules.notifications.models import NotificationEvent
from app.modules.outcomes.models import SignalOutcome
from app.modules.product_readiness.models import ProductReadinessRun
from app.modules.provider_health.models import ProviderHealthSnapshot
from app.modules.read_models.models import SignalCardReadModel
from app.modules.runtime_supervisor.service import RuntimeSupervisorService
from app.modules.symbols.models import Symbol
from app.modules.trading_journal.models import JournalEntry
from app.modules.workspace_overview.schemas import (
    WorkspaceOverviewItem,
    WorkspaceOverviewNotificationSummary,
    WorkspaceOverviewQuery,
    WorkspaceOverviewResponse,
    WorkspaceOverviewStatus,
)
from app.modules.workspaces.repository import WorkspaceRepository

REVIEW_BUCKETS = {"high_quality_context"}
CONFIRMATION_BUCKETS = {"needs_confirmation", "conflicted", "review_required"}
AVOID_BUCKETS = {"avoid_or_no_directional_signal", "stale_or_data_issue"}
PENDING_ACTION_STATUSES = {"pending", "due", "running"}
UNREAD_NOTIFICATION_STATUSES = {"unread"}
ACKNOWLEDGED_NOTIFICATION_STATUSES = {"acknowledged"}


class WorkspaceOverviewService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.workspace_repository = WorkspaceRepository(session)

    async def build_overview(
        self,
        workspace_id: UUID,
        query: WorkspaceOverviewQuery,
    ) -> WorkspaceOverviewResponse:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")

        missing_sections: list[str] = []
        warnings: list[str] = []
        max_review_items = self.settings.workspace_overview_max_review_items
        max_action_items = self.settings.workspace_overview_max_action_items
        max_warnings = self.settings.workspace_overview_max_warnings

        readiness = await self.safe_section(
            "readiness",
            missing_sections,
            warnings,
            lambda: self.build_readiness(workspace_id),
            empty_status("unknown", "Readiness unavailable", "No readiness run is available."),
        )
        provider_health = await self.safe_section(
            "providerHealth",
            missing_sections,
            warnings,
            lambda: self.build_provider_health(workspace_id),
            empty_status(
                "unknown",
                "Provider health unavailable",
                "No provider health snapshot is available.",
            ),
        )
        data_freshness = await self.safe_section(
            "dataFreshness",
            missing_sections,
            warnings,
            lambda: self.build_data_freshness(workspace_id),
            empty_status(
                "unknown", "Data freshness unavailable", "No data freshness snapshot is available."
            ),
        )
        daily_brief = await self.safe_section(
            "dailyBrief",
            missing_sections,
            warnings,
            lambda: self.build_daily_brief(workspace_id),
            empty_status("missing", "Daily brief missing", "No daily brief is available."),
        )
        workflow = await self.safe_section(
            "workflow",
            missing_sections,
            warnings,
            lambda: self.build_workflow(workspace_id),
            empty_status("missing", "Workflow missing", "No daily workflow run is available."),
        )
        signal_sections = await self.safe_section(
            "signalPriority",
            missing_sections,
            warnings,
            lambda: self.build_signal_sections(workspace_id, query.include_read_models),
            {"review_first": [], "needs_confirmation": [], "avoid_conditions": []},
        )
        outcome_updates = await self.safe_section(
            "outcomes",
            missing_sections,
            warnings,
            lambda: self.list_outcome_updates(workspace_id, max_review_items),
            [],
        )
        pending_actions = await self.safe_section(
            "pendingActions",
            missing_sections,
            warnings,
            lambda: self.list_pending_actions(workspace_id, max_action_items),
            [],
        )
        notifications = await self.safe_section(
            "notifications",
            missing_sections,
            warnings,
            lambda: self.build_notifications(workspace_id, query.include_notifications),
            WorkspaceOverviewNotificationSummary(),
        )
        journal_prompts = await self.safe_section(
            "journal",
            missing_sections,
            warnings,
            lambda: self.build_journal_prompts(
                workspace_id, signal_sections["review_first"], query.include_journal
            ),
            [],
        )
        quality_warnings = await self.safe_section(
            "quality",
            missing_sections,
            warnings,
            lambda: self.list_quality_warnings(workspace_id, query.include_quality, max_warnings),
            [],
        )
        navigation_hints = self.build_navigation_hints(
            workspace_id, readiness, provider_health, data_freshness
        )

        return WorkspaceOverviewResponse(
            workspace_id=workspace_id,
            generated_at=datetime.now(UTC),
            overview_version=self.settings.workspace_overview_version,
            readiness=readiness,
            data_freshness=data_freshness,
            provider_health=provider_health,
            daily_brief=daily_brief,
            workflow=workflow,
            review_first=signal_sections["review_first"][:max_review_items],
            needs_confirmation=signal_sections["needs_confirmation"][:max_review_items],
            avoid_conditions=signal_sections["avoid_conditions"][:max_review_items],
            outcome_updates=outcome_updates[:max_review_items],
            pending_actions=pending_actions[:max_action_items],
            notifications=notifications,
            journal_prompts=journal_prompts[:max_review_items],
            quality_warnings=quality_warnings[:max_warnings],
            navigation_hints=navigation_hints,
            missing_sections=missing_sections,
            warnings=warnings[:max_warnings],
        )

    async def safe_section[T](
        self,
        name: str,
        missing_sections: list[str],
        warnings: list[str],
        factory: Callable[[], Awaitable[T]],
        fallback: T,
    ) -> T:
        try:
            return await factory()
        except AppError:
            raise
        except Exception:
            missing_sections.append(name)
            warnings.append(f"{name} is unavailable in the current workspace context.")
            return fallback

    async def build_readiness(self, workspace_id: UUID) -> WorkspaceOverviewStatus:
        run = await self.scalar_one_or_none(
            select(ProductReadinessRun)
            .where(ProductReadinessRun.workspace_id == workspace_id)
            .order_by(ProductReadinessRun.created_at.desc())
            .limit(1)
        )
        if run is None:
            return empty_status(
                "missing", "Readiness missing", "Run readiness before daily review."
            )
        blocker_count = len(run.blockers_json)
        warning_count = len(run.warnings_json)
        return WorkspaceOverviewStatus(
            status=run.readiness_label,
            label=humanize(run.readiness_label),
            summary=run.summary,
            metadata_json={
                "runId": str(run.id),
                "score": decimal_to_float(run.readiness_score),
                "blockerCount": blocker_count,
                "warningCount": warning_count,
                "createdAt": run.created_at.isoformat(),
            },
        )

    async def build_provider_health(self, workspace_id: UUID) -> WorkspaceOverviewStatus:
        snapshots = await self.list_scalars(
            select(ProviderHealthSnapshot)
            .where(ProviderHealthSnapshot.workspace_id == workspace_id)
            .order_by(ProviderHealthSnapshot.created_at.desc())
            .limit(500)
        )
        if not snapshots:
            return empty_status(
                "missing", "Provider health missing", "Provider health has not been recorded."
            )
        counts = count_by(snapshots, "status")
        failing_count = counts.get("failing", 0) + counts.get("unavailable", 0)
        stale_count = counts.get("stale", 0) + counts.get("degraded", 0)
        status = "healthy" if failing_count == 0 and stale_count == 0 else "degraded"
        if failing_count > 0:
            status = "failing"
        return WorkspaceOverviewStatus(
            status=status,
            label=humanize(status),
            summary=(
                f"{counts.get('healthy', 0)} healthy snapshots, "
                f"{stale_count} degraded or stale, "
                f"{failing_count} failing or unavailable."
            ),
            metadata_json={
                "counts": counts,
                "snapshotCount": len(snapshots),
                "missingCandleCount": sum(snapshot.missing_candle_count for snapshot in snapshots),
                "latestSnapshotAt": snapshots[0].created_at.isoformat(),
            },
        )

    async def build_data_freshness(self, workspace_id: UUID) -> WorkspaceOverviewStatus:
        snapshots = await self.list_scalars(
            select(ProviderHealthSnapshot)
            .where(ProviderHealthSnapshot.workspace_id == workspace_id)
            .order_by(ProviderHealthSnapshot.created_at.desc())
            .limit(500)
        )
        if not snapshots:
            return empty_status(
                "missing", "Data freshness missing", "Freshness has not been recorded."
            )
        freshness_counts = count_by(snapshots, "freshness_label")
        ready_count = freshness_counts.get("fresh", 0)
        stale_count = (
            freshness_counts.get("stale", 0)
            + freshness_counts.get("delayed", 0)
            + freshness_counts.get("no_data", 0)
        )
        status = "fresh" if stale_count == 0 else "degraded"
        return WorkspaceOverviewStatus(
            status=status,
            label="Data fresh" if status == "fresh" else "Data review recommended",
            summary=f"{ready_count} data contexts are fresh and {stale_count} need review.",
            metadata_json={
                "freshnessCounts": freshness_counts,
                "freshCount": ready_count,
                "staleOrDegradedCount": stale_count,
            },
        )

    async def build_daily_brief(self, workspace_id: UUID) -> WorkspaceOverviewStatus:
        run = await self.scalar_one_or_none(
            select(DailyBriefRun)
            .where(DailyBriefRun.workspace_id == workspace_id)
            .order_by(DailyBriefRun.generated_at.desc(), DailyBriefRun.created_at.desc())
            .limit(1)
        )
        if run is None:
            return empty_status(
                "missing",
                "Daily brief missing",
                "Generate a daily brief to summarize stored artifacts.",
            )
        title = str(run.summary_json.get("title") or "Daily brief available")
        summary = str(run.summary_json.get("summary") or f"Latest brief status is {run.status}.")
        return WorkspaceOverviewStatus(
            status=run.status,
            label=title,
            summary=summary,
            metadata_json={
                "briefRunId": str(run.id),
                "briefType": run.brief_type,
                "generatedAt": run.generated_at.isoformat(),
                "warningCount": len(run.warnings_json),
            },
        )

    async def build_workflow(self, workspace_id: UUID) -> WorkspaceOverviewStatus:
        run = await self.scalar_one_or_none(
            select(DailyWorkflowRun)
            .where(DailyWorkflowRun.workspace_id == workspace_id)
            .order_by(DailyWorkflowRun.created_at.desc())
            .limit(1)
        )
        runtime_health = await RuntimeSupervisorService(
            self.session, self.settings
        ).summarize_runtime_health(workspace_id)
        if run is None:
            return WorkspaceOverviewStatus(
                status=runtime_health.status,
                label="Workflow not started",
                summary="No daily workflow run is recorded for this workspace.",
                metadata_json=runtime_health.model_dump(mode="json", by_alias=True),
            )
        metadata = runtime_health.model_dump(mode="json", by_alias=True)
        metadata.update(
            {
                "workflowRunId": str(run.id),
                "workflowType": run.workflow_type,
                "createdAt": run.created_at.isoformat(),
                "artifactIds": run.created_artifact_ids_json,
            }
        )
        return WorkspaceOverviewStatus(
            status=run.status,
            label=humanize(run.status),
            summary=run.summary,
            metadata_json=metadata,
        )

    async def build_signal_sections(
        self,
        workspace_id: UUID,
        include_read_models: bool,
    ) -> dict[str, list[WorkspaceOverviewItem]]:
        if not include_read_models:
            return {"review_first": [], "needs_confirmation": [], "avoid_conditions": []}
        rows = await self.session.execute(
            select(SignalCardReadModel, Symbol)
            .join(Symbol, Symbol.id == SignalCardReadModel.symbol_id)
            .where(
                SignalCardReadModel.workspace_id == workspace_id,
                SignalCardReadModel.read_model_version == self.settings.read_model_version,
            )
            .order_by(
                SignalCardReadModel.priority_score.desc().nullslast(),
                SignalCardReadModel.updated_at.desc(),
            )
            .limit(200)
        )
        review_first: list[WorkspaceOverviewItem] = []
        needs_confirmation: list[WorkspaceOverviewItem] = []
        avoid_conditions: list[WorkspaceOverviewItem] = []
        for card, symbol in rows.all():
            item = signal_card_item(card, symbol)
            bucket = card.review_bucket or ""
            if bucket in REVIEW_BUCKETS:
                review_first.append(item)
            elif bucket in CONFIRMATION_BUCKETS:
                needs_confirmation.append(item)
            elif bucket in AVOID_BUCKETS:
                avoid_conditions.append(item)
        return {
            "review_first": review_first,
            "needs_confirmation": needs_confirmation,
            "avoid_conditions": avoid_conditions,
        }

    async def list_outcome_updates(
        self, workspace_id: UUID, limit: int
    ) -> list[WorkspaceOverviewItem]:
        rows = await self.session.execute(
            select(SignalOutcome, Symbol)
            .join(Symbol, Symbol.id == SignalOutcome.symbol_id)
            .where(SignalOutcome.workspace_id == workspace_id)
            .order_by(SignalOutcome.updated_at.desc())
            .limit(limit)
        )
        return [
            WorkspaceOverviewItem(
                id=str(outcome.id),
                title=f"{symbol.symbol} {outcome.timeframe}",
                summary=outcome_summary(outcome),
                reason=humanize(outcome.outcome_label),
                symbol_id=outcome.symbol_id,
                symbol=symbol.symbol,
                timeframe=outcome.timeframe,
                signal_id=outcome.signal_id,
                analysis_run_id=outcome.analysis_run_id,
                bias=outcome.bias,
                href=f"/signals/{outcome.signal_id}",
                metadata_json={
                    "horizonMinutes": outcome.horizon_minutes,
                    "evaluationStatus": outcome.evaluation_status,
                    "updatedAt": outcome.updated_at.isoformat(),
                },
            )
            for outcome, symbol in rows.all()
        ]

    async def list_pending_actions(
        self, workspace_id: UUID, limit: int
    ) -> list[WorkspaceOverviewItem]:
        actions = await self.list_scalars(
            select(ReasoningActionItem)
            .where(
                ReasoningActionItem.workspace_id == workspace_id,
                ReasoningActionItem.status.in_(PENDING_ACTION_STATUSES),
            )
            .order_by(
                ReasoningActionItem.due_at.asc().nullsfirst(), ReasoningActionItem.created_at.desc()
            )
            .limit(limit)
        )
        return [
            WorkspaceOverviewItem(
                id=str(action.id),
                title=humanize(action.action_type),
                summary=action.error_message or "Backend-safe next step is pending.",
                reason=humanize(action.priority),
                signal_id=action.signal_id,
                analysis_run_id=action.analysis_run_id,
                href=f"/signals/{action.signal_id}" if action.signal_id else "/command-center",
                metadata_json={
                    "status": action.status,
                    "dueAt": action.due_at.isoformat() if action.due_at else None,
                    "sourceType": action.source_type,
                },
            )
            for action in actions
        ]

    async def build_notifications(
        self,
        workspace_id: UUID,
        include_notifications: bool,
    ) -> WorkspaceOverviewNotificationSummary:
        if not include_notifications:
            return WorkspaceOverviewNotificationSummary()
        counts = await self.session.execute(
            select(NotificationEvent.inbox_status, func.count(NotificationEvent.id))
            .where(NotificationEvent.workspace_id == workspace_id)
            .group_by(NotificationEvent.inbox_status)
        )
        count_map = {str(status): int(count) for status, count in counts.all()}
        events = await self.list_scalars(
            select(NotificationEvent)
            .where(NotificationEvent.workspace_id == workspace_id)
            .order_by(NotificationEvent.created_at.desc())
            .limit(5)
        )
        return WorkspaceOverviewNotificationSummary(
            unread_count=sum(count_map.get(status, 0) for status in UNREAD_NOTIFICATION_STATUSES),
            acknowledged_count=sum(
                count_map.get(status, 0) for status in ACKNOWLEDGED_NOTIFICATION_STATUSES
            ),
            latest=[
                WorkspaceOverviewItem(
                    id=str(event.id),
                    title=event.title,
                    summary=event.summary,
                    reason=humanize(event.severity),
                    href="/notifications",
                    metadata_json={
                        "eventType": event.event_type,
                        "createdAt": event.created_at.isoformat(),
                    },
                )
                for event in events
            ],
            metadata_json={"counts": count_map},
        )

    async def build_journal_prompts(
        self,
        workspace_id: UUID,
        review_first: list[WorkspaceOverviewItem],
        include_journal: bool,
    ) -> list[WorkspaceOverviewItem]:
        if not include_journal or not review_first:
            return []
        signal_ids = [item.signal_id for item in review_first if item.signal_id is not None]
        if not signal_ids:
            return []
        existing = await self.list_scalars(
            select(JournalEntry.signal_id).where(
                JournalEntry.workspace_id == workspace_id, JournalEntry.signal_id.in_(signal_ids)
            )
        )
        journaled_signal_ids = {signal_id for signal_id in existing if signal_id is not None}
        prompts = []
        for item in review_first:
            if item.signal_id is None or item.signal_id in journaled_signal_ids:
                continue
            prompt_summary = (
                f"{item.symbol or 'Setup'} {item.timeframe or ''} has review context "
                "without a journal note."
            ).strip()
            prompts.append(
                WorkspaceOverviewItem(
                    id=f"journal:{item.signal_id}",
                    title="Journal reflection",
                    summary=prompt_summary,
                    reason=item.reason,
                    signal_id=item.signal_id,
                    symbol_id=item.symbol_id,
                    symbol=item.symbol,
                    timeframe=item.timeframe,
                    href=item.href,
                    metadata_json={"source": "workspace_overview"},
                )
            )
        return prompts

    async def list_quality_warnings(
        self,
        workspace_id: UUID,
        include_quality: bool,
        limit: int,
    ) -> list[WorkspaceOverviewItem]:
        if not include_quality:
            return []
        findings = await self.list_scalars(
            select(DataQualityFinding)
            .where(
                DataQualityFinding.workspace_id == workspace_id,
                DataQualityFinding.severity.in_(["medium", "high"]),
            )
            .order_by(DataQualityFinding.created_at.desc())
            .limit(limit)
        )
        return [
            WorkspaceOverviewItem(
                id=str(finding.id),
                title=humanize(finding.finding_type),
                summary=finding.message,
                reason=humanize(finding.severity),
                href="/quality",
                metadata_json={
                    "severity": finding.severity,
                    "createdAt": finding.created_at.isoformat(),
                },
            )
            for finding in findings
        ]

    def build_navigation_hints(
        self,
        workspace_id: UUID,
        readiness: WorkspaceOverviewStatus,
        provider_health: WorkspaceOverviewStatus,
        data_freshness: WorkspaceOverviewStatus,
    ) -> list[WorkspaceOverviewItem]:
        hints = [
            navigation_item(
                "readiness",
                "Open readiness",
                "Validate daily-use setup.",
                f"/readiness?workspaceId={workspace_id}",
            ),
            navigation_item(
                "data",
                "Open data onboarding",
                "Review provider and freshness context.",
                f"/data/onboarding?workspaceId={workspace_id}",
            ),
            navigation_item(
                "scanner",
                "Open scanner",
                "Run deterministic scans explicitly.",
                f"/scanner?workspaceId={workspace_id}",
            ),
            navigation_item(
                "brief",
                "Open brief",
                "Read latest daily brief.",
                f"/brief?workspaceId={workspace_id}",
            ),
            navigation_item(
                "triage",
                "Open triage",
                "Review setup context queues.",
                f"/triage?workspaceId={workspace_id}",
            ),
        ]
        if readiness.status in {"blocked", "needs_setup", "unknown", "missing"}:
            hints.insert(
                0,
                navigation_item(
                    "setup",
                    "Open setup",
                    "Complete setup review before daily workflow.",
                    f"/setup?workspaceId={workspace_id}",
                ),
            )
        if provider_health.status in {"failing", "degraded"} or data_freshness.status == "degraded":
            hints.insert(
                0,
                navigation_item(
                    "data-review",
                    "Review data freshness",
                    "Provider or freshness context needs review.",
                    f"/data/onboarding?workspaceId={workspace_id}",
                ),
            )
        return hints

    async def scalar_one_or_none[T](self, statement: Select[tuple[T]]) -> T | None:
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_scalars[T](self, statement: Select[tuple[T]]) -> list[T]:
        result = await self.session.execute(statement)
        return list(result.scalars().all())


def signal_card_item(card: SignalCardReadModel, symbol: Symbol) -> WorkspaceOverviewItem:
    reason = first_text(card.evidence_summary_json, "summary") or first_text(
        card.warning_summary_json, "summary"
    )
    return WorkspaceOverviewItem(
        id=str(card.id),
        title=f"{symbol.symbol} {card.timeframe}",
        summary=card.searchable_text[:280] or "Setup context is available.",
        reason=reason
        or humanize(card.review_bucket or card.priority_label or "Review recommended"),
        symbol_id=card.symbol_id,
        symbol=symbol.symbol,
        timeframe=card.timeframe,
        signal_id=card.signal_id,
        analysis_run_id=card.analysis_run_id,
        bias=card.bias,
        confidence_label=card.confidence_label,
        priority_label=card.priority_label,
        setup_quality_label=card.setup_quality_label,
        freshness_label=card.freshness_label,
        data_quality_label=card.data_quality_label,
        href=f"/signals/{card.signal_id}",
        metadata_json={
            "priorityScore": decimal_to_float(card.priority_score),
            "reviewBucket": card.review_bucket,
            "readinessLabel": card.readiness_label,
            "updatedAt": card.updated_at.isoformat(),
        },
    )


def outcome_summary(outcome: SignalOutcome) -> str:
    if outcome.reversal_detected:
        return "Observed reversal context is available."
    if outcome.direction_followed is True:
        return "Observed follow-through context is available."
    if outcome.direction_followed is False:
        return "No follow-through observed for the stored horizon."
    return "Outcome ready for review."


def navigation_item(id_value: str, title: str, summary: str, href: str) -> WorkspaceOverviewItem:
    return WorkspaceOverviewItem(
        id=id_value,
        title=title,
        summary=summary,
        href=href,
        metadata_json={"source": "workspace_overview"},
    )


def empty_status(status: str, label: str, summary: str) -> WorkspaceOverviewStatus:
    return WorkspaceOverviewStatus(status=status, label=label, summary=summary, metadata_json={})


def count_by(items: list[object], attribute_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(getattr(item, attribute_name))
        counts[value] = counts.get(value, 0) + 1
    return counts


def first_text(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value.strip() else None


def decimal_to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def humanize(value: str | None) -> str:
    if not value:
        return "Not available"
    return value.replace("_", " ").strip().title()
