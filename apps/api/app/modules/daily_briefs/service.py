from datetime import UTC, date, datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.daily_briefs.builder import (
    BuiltDailyBrief,
    DailyBriefArtifacts,
    DailyBriefBuilder,
    DailyBriefBuildInput,
    DailyBriefDraftItem,
)
from app.modules.daily_briefs.models import (
    DailyBriefItem,
    DailyBriefRun,
    DailyBriefStatus,
    DailyBriefType,
)
from app.modules.daily_briefs.repository import DailyBriefRepository, DailyBriefScope
from app.modules.daily_briefs.schemas import (
    DailyBriefCreate,
    DailyBriefFilters,
    DailyBriefRunListFilters,
)
from app.modules.daily_briefs.sections import to_json_value
from app.modules.workspaces.repository import WorkspaceRepository


class DailyBriefService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: DailyBriefRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or DailyBriefRepository(session)
        self.workspace_repository = WorkspaceRepository(session)
        self.builder = DailyBriefBuilder()

    async def create_daily_brief(
        self,
        workspace_id: UUID,
        brief_date: date,
        timezone: str,
        filters: DailyBriefFilters,
    ) -> DailyBriefRun:
        timezone_info = ZoneInfo(timezone)
        return await self.create_brief(
            DailyBriefCreate(
                workspace_id=workspace_id,
                brief_type=DailyBriefType.DAILY,
                period_start=datetime.combine(brief_date, time.min, tzinfo=timezone_info),
                period_end=datetime.combine(brief_date, time.max, tzinfo=timezone_info),
                timezone=timezone,
                filters=filters,
            )
        )

    async def create_session_brief(
        self,
        workspace_id: UUID,
        session_label: str,
        brief_date: date,
        filters: DailyBriefFilters,
        timezone: str | None = None,
    ) -> DailyBriefRun:
        resolved_timezone = timezone or self.settings.daily_brief_default_timezone
        timezone_info = ZoneInfo(resolved_timezone)
        return await self.create_brief(
            DailyBriefCreate(
                workspace_id=workspace_id,
                brief_type=DailyBriefType.SESSION,
                period_start=datetime.combine(brief_date, time.min, tzinfo=timezone_info),
                period_end=datetime.combine(brief_date, time.max, tzinfo=timezone_info),
                timezone=resolved_timezone,
                filters=filters,
            ),
            session_label=session_label,
        )

    async def create_intraday_brief(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        filters: DailyBriefFilters,
        timezone: str | None = None,
    ) -> DailyBriefRun:
        return await self.create_brief(
            DailyBriefCreate(
                workspace_id=workspace_id,
                brief_type=DailyBriefType.INTRADAY,
                period_start=period_start,
                period_end=period_end,
                timezone=timezone or self.settings.daily_brief_default_timezone,
                filters=filters,
            )
        )

    async def create_watchlist_brief(
        self,
        workspace_id: UUID,
        watchlist_id: UUID,
        period_start: datetime,
        period_end: datetime,
        filters: DailyBriefFilters,
        timezone: str | None = None,
    ) -> DailyBriefRun:
        return await self.create_brief(
            DailyBriefCreate(
                workspace_id=workspace_id,
                brief_type=DailyBriefType.WATCHLIST,
                period_start=period_start,
                period_end=period_end,
                timezone=timezone or self.settings.daily_brief_default_timezone,
                watchlist_id=watchlist_id,
                filters=filters,
            )
        )

    async def create_brief(
        self,
        payload: DailyBriefCreate,
        session_label: str | None = None,
    ) -> DailyBriefRun:
        await self.validate_workspace(payload.workspace_id)
        max_items = self.settings.daily_brief_max_items
        filters_json = daily_brief_filters_json(payload, max_items, session_label)
        run = DailyBriefRun(
            workspace_id=payload.workspace_id,
            digest_id=None,
            watchlist_id=payload.watchlist_id,
            status=DailyBriefStatus.PENDING.value,
            brief_type=payload.brief_type.value,
            brief_version=self.settings.daily_brief_version,
            period_start=payload.period_start,
            period_end=payload.period_end,
            timezone=payload.timezone,
            filters_json=filters_json,
            summary_json={},
            sections_json={},
            warnings_json=[],
            generated_at=datetime.now(UTC),
        )
        try:
            created_run = await self.repository.create_run(run)
            built = await self.build_brief_payload(payload, filters_json, max_items, session_label)
            created_run.digest_id = built.digest_id
            created_run.summary_json = built.summary_json
            created_run.sections_json = built.sections_json
            created_run.warnings_json = built.warnings_json
            created_run.status = (
                DailyBriefStatus.COMPLETED_WITH_WARNINGS.value
                if built.warnings_json
                else DailyBriefStatus.COMPLETED.value
            )
            await self.repository.update_run(created_run)
            await self.repository.create_items(
                [
                    draft_item_to_model(
                        draft=draft,
                        workspace_id=created_run.workspace_id,
                        brief_run_id=created_run.id,
                        sort_order=index,
                    )
                    for index, draft in enumerate(built.items, start=1)
                ]
            )
            await self.session.commit()
            await self.session.refresh(created_run)
            return created_run
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409, "daily_brief_conflict", "Daily brief could not be persisted"
            ) from error

    async def build_brief_payload(
        self,
        payload: DailyBriefCreate,
        filters_json: dict[str, object],
        max_items: int,
        session_label: str | None = None,
    ) -> BuiltDailyBrief:
        scope = await self.resolve_scope(
            payload.workspace_id, payload.watchlist_id, payload.filters
        )
        artifacts = await self.load_artifacts(
            workspace_id=payload.workspace_id,
            period_start=payload.period_start,
            period_end=payload.period_end,
            scope=scope,
            session_label=session_label,
            limit=max_items * 2,
        )
        return self.builder.build(
            DailyBriefBuildInput(
                workspace_id=payload.workspace_id,
                brief_type=payload.brief_type,
                period_start=payload.period_start,
                period_end=payload.period_end,
                timezone=payload.timezone,
                filters_json=filters_json,
                max_items=max_items,
                review_first_limit=self.settings.daily_brief_review_first_limit,
                outcome_update_limit=self.settings.daily_brief_outcome_update_limit,
                action_item_limit=self.settings.daily_brief_action_item_limit,
                session_label=session_label,
                watchlist_id=payload.watchlist_id,
            ),
            artifacts,
        )

    async def get_brief(self, brief_id: UUID) -> DailyBriefRun:
        run = await self.repository.get_run(brief_id)
        if run is None:
            raise AppError(404, "daily_brief_not_found", "Daily brief not found")
        return run

    async def list_briefs(self, filters: DailyBriefRunListFilters) -> list[DailyBriefRun]:
        return await self.repository.list_runs(
            workspace_id=filters.workspace_id,
            brief_type=filters.brief_type.value if filters.brief_type is not None else None,
            status=filters.status.value if filters.status is not None else None,
            watchlist_id=filters.watchlist_id,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def get_latest_brief(
        self,
        workspace_id: UUID,
        brief_type: DailyBriefType | None = DailyBriefType.DAILY,
        watchlist_id: UUID | None = None,
    ) -> DailyBriefRun:
        run = await self.repository.get_latest_run(
            workspace_id=workspace_id,
            brief_type=brief_type.value if brief_type is not None else None,
            watchlist_id=watchlist_id,
        )
        if run is None:
            raise AppError(404, "daily_brief_not_found", "Daily brief not found")
        return run

    async def list_brief_items(
        self,
        brief_id: UUID,
        limit: int,
        offset: int,
        item_type: str | None = None,
        priority: str | None = None,
    ) -> list[DailyBriefItem]:
        await self.get_brief(brief_id)
        return await self.repository.list_items(
            brief_id=brief_id,
            item_type=item_type,
            priority=priority,
            limit=limit,
            offset=offset,
        )

    async def validate_workspace(self, workspace_id: UUID) -> None:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")

    async def resolve_scope(
        self,
        workspace_id: UUID,
        watchlist_id: UUID | None,
        filters: DailyBriefFilters,
    ) -> DailyBriefScope:
        symbol_ids = [*filters.symbol_ids]
        timeframes = [timeframe.value for timeframe in filters.timeframes]
        is_empty = False
        if watchlist_id is not None:
            watchlist_scope = await self.repository.list_watchlist_scope(workspace_id, watchlist_id)
            if not watchlist_scope:
                is_empty = True
            watchlist_symbol_ids = list(
                dict.fromkeys(symbol_id for symbol_id, _ in watchlist_scope)
            )
            watchlist_timeframes = list(
                dict.fromkeys(timeframe for _, timeframe in watchlist_scope)
            )
            symbol_ids = intersect_or_default(symbol_ids, watchlist_symbol_ids)
            timeframes = intersect_or_default(timeframes, watchlist_timeframes)
            is_empty = is_empty or not symbol_ids or not timeframes
        return DailyBriefScope(
            watchlist_id=watchlist_id,
            symbol_ids=symbol_ids,
            timeframes=timeframes,
            is_empty=is_empty,
        )

    async def load_artifacts(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DailyBriefScope,
        session_label: str | None,
        limit: int,
    ) -> DailyBriefArtifacts:
        return DailyBriefArtifacts(
            digest_context=await self.repository.get_latest_signal_digest(
                workspace_id=workspace_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
            ),
            priority_signals=await self.repository.list_priority_signals(
                workspace_id=workspace_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            recent_signals=await self.repository.list_recent_signals(
                workspace_id=workspace_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            memory_contexts=await self.repository.list_memory_contexts(
                workspace_id=workspace_id,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            provider_health=await self.repository.list_provider_health_contexts(
                workspace_id=workspace_id,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            latest_candles=await self.repository.list_latest_final_candles(
                workspace_id=workspace_id,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            data_quality=await self.repository.list_data_quality_contexts(
                workspace_id=workspace_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            outcomes=await self.repository.list_outcome_contexts(
                workspace_id=workspace_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            pending_actions=await self.repository.list_pending_actions(
                workspace_id=workspace_id,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            due_scans=await self.repository.list_due_scan_contexts(
                workspace_id=workspace_id,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            market_contexts=await self.repository.list_market_contexts(
                workspace_id=workspace_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            journal_contexts=await self.repository.list_journal_contexts(
                workspace_id=workspace_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
        )


def daily_brief_filters_json(
    payload: DailyBriefCreate,
    max_items: int,
    session_label: str | None,
) -> dict[str, object]:
    filters_json = payload.filters.model_dump(mode="json", by_alias=True)
    filters_json["maxItems"] = max_items
    filters_json["watchlistId"] = str(payload.watchlist_id) if payload.watchlist_id else None
    filters_json["sessionLabel"] = session_label
    return filters_json


def draft_item_to_model(
    draft: DailyBriefDraftItem,
    workspace_id: UUID,
    brief_run_id: UUID,
    sort_order: int,
) -> DailyBriefItem:
    return DailyBriefItem(
        workspace_id=workspace_id,
        brief_run_id=brief_run_id,
        item_type=draft.item_type.value,
        priority=draft.priority.value,
        symbol_id=draft.symbol_id,
        signal_id=draft.signal_id,
        analysis_run_id=draft.analysis_run_id,
        outcome_id=draft.outcome_id,
        action_item_id=draft.action_item_id,
        setup_context_id=draft.setup_context_id,
        source_type=draft.source_type,
        source_id=draft.source_id,
        title=draft.title,
        summary=draft.summary,
        reason=draft.reason,
        tags_json=[str(tag) for tag in draft.tags],
        metadata_json=to_json_value(draft.metadata),
        sort_order=sort_order,
    )


def intersect_or_default[T](current: list[T], candidates: list[T]) -> list[T]:
    if not current:
        return candidates
    candidate_set = set(candidates)
    return [item for item in current if item in candidate_set]
