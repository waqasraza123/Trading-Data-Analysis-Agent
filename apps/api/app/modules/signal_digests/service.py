from datetime import date, datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.signal_digests.builder import (
    BuiltSignalDigest,
    SignalDigestArtifacts,
    SignalDigestBuilder,
    SignalDigestBuildInput,
    SignalDigestDraftItem,
    to_json_value,
)
from app.modules.signal_digests.models import (
    SignalDigestItem,
    SignalDigestPriority,
    SignalDigestRun,
    SignalDigestStatus,
    SignalDigestType,
)
from app.modules.signal_digests.repository import DigestScope, SignalDigestRepository
from app.modules.signal_digests.schemas import (
    SignalDigestCreate,
    SignalDigestFilters,
    SignalDigestRunListFilters,
)
from app.modules.workspaces.repository import WorkspaceRepository


class SignalDigestService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: SignalDigestRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or SignalDigestRepository(session)
        self.workspace_repository = WorkspaceRepository(session)
        self.builder = SignalDigestBuilder()

    async def create_digest(self, payload: SignalDigestCreate) -> SignalDigestRun:
        await self.validate_workspace(payload.workspace_id)
        max_items = min(
            payload.max_items or self.settings.signal_digest_max_items,
            self.settings.signal_digest_max_items,
        )
        filters_json = digest_filters_json(payload.filters, max_items)
        run = SignalDigestRun(
            workspace_id=payload.workspace_id,
            digest_type=payload.digest_type.value,
            status=SignalDigestStatus.PENDING.value,
            digest_version=self.settings.signal_digest_version,
            title="Signal digest pending",
            period_start=payload.period_start,
            period_end=payload.period_end,
            timezone=payload.timezone,
            filters_json=filters_json,
            summary_json={},
            section_counts_json={},
            warnings_json=[],
        )
        try:
            created_run = await self.repository.create_run(run)
            built = await self.build_digest_payload(
                payload=payload,
                filters_json=filters_json,
                max_items=max_items,
            )
            created_run.title = built.title
            created_run.summary_json = built.summary_json
            created_run.section_counts_json = built.section_counts_json
            created_run.warnings_json = built.warnings_json
            created_run.status = (
                SignalDigestStatus.COMPLETED_WITH_WARNINGS.value
                if built.warnings_json
                else SignalDigestStatus.COMPLETED.value
            )
            await self.repository.update_run(created_run)
            await self.repository.create_items(
                [
                    draft_item_to_model(
                        draft=draft,
                        workspace_id=created_run.workspace_id,
                        digest_run_id=created_run.id,
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
                409,
                "signal_digest_conflict",
                "Signal digest could not be persisted",
            ) from error

    async def build_digest_payload(
        self,
        payload: SignalDigestCreate,
        filters_json: dict[str, object],
        max_items: int,
        session_label: str | None = None,
    ) -> BuiltSignalDigest:
        scope = await self.resolve_scope(payload.workspace_id, payload.filters)
        artifacts = await self.load_artifacts(
            workspace_id=payload.workspace_id,
            period_start=payload.period_start,
            period_end=payload.period_end,
            scope=scope,
            session_label=session_label,
            limit=max_items * 2,
        )
        return self.builder.build(
            SignalDigestBuildInput(
                workspace_id=payload.workspace_id,
                digest_type=payload.digest_type,
                period_start=payload.period_start,
                period_end=payload.period_end,
                timezone=payload.timezone,
                filters_json=filters_json,
                max_items=max_items,
                high_confidence_threshold=self.settings.signal_digest_high_confidence_threshold,
                stale_data_priority=SignalDigestPriority(
                    self.settings.signal_digest_stale_data_priority
                ),
                session_label=session_label,
            ),
            artifacts,
        )

    async def get_digest(self, digest_id: UUID) -> SignalDigestRun:
        run = await self.repository.get_run(digest_id)
        if run is None:
            raise AppError(404, "signal_digest_not_found", "Signal digest not found")
        return run

    async def list_digests(
        self,
        filters: SignalDigestRunListFilters,
    ) -> list[SignalDigestRun]:
        return await self.repository.list_runs(
            workspace_id=filters.workspace_id,
            digest_type=filters.digest_type.value if filters.digest_type is not None else None,
            status=filters.status.value if filters.status is not None else None,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def list_digest_items(
        self,
        digest_id: UUID,
        limit: int,
        offset: int,
        item_type: str | None = None,
    ) -> list[SignalDigestItem]:
        await self.get_digest(digest_id)
        return await self.repository.list_items(
            digest_id=digest_id,
            item_type=item_type,
            limit=limit,
            offset=offset,
        )

    async def build_daily_digest(
        self,
        workspace_id: UUID,
        digest_date: date,
        timezone: str,
        filters: SignalDigestFilters,
        max_items: int | None = None,
    ) -> SignalDigestRun:
        timezone_info = ZoneInfo(timezone)
        return await self.create_digest(
            SignalDigestCreate(
                workspace_id=workspace_id,
                digest_type=SignalDigestType.DAILY,
                period_start=datetime.combine(digest_date, time.min, tzinfo=timezone_info),
                period_end=datetime.combine(digest_date, time.max, tzinfo=timezone_info),
                timezone=timezone,
                filters=filters,
                max_items=max_items,
            )
        )

    async def build_session_digest(
        self,
        workspace_id: UUID,
        session_label: str,
        digest_date: date,
        timezone: str,
        filters: SignalDigestFilters,
        max_items: int | None = None,
    ) -> SignalDigestRun:
        timezone_info = ZoneInfo(timezone)
        request = SignalDigestCreate(
            workspace_id=workspace_id,
            digest_type=SignalDigestType.SESSION,
            period_start=datetime.combine(digest_date, time.min, tzinfo=timezone_info),
            period_end=datetime.combine(digest_date, time.max, tzinfo=timezone_info),
            timezone=timezone,
            filters=filters,
            max_items=max_items,
        )
        await self.validate_workspace(workspace_id)
        max_items_resolved = min(
            max_items or self.settings.signal_digest_max_items,
            self.settings.signal_digest_max_items,
        )
        filters_json = digest_filters_json(filters, max_items_resolved)
        filters_json["sessionLabel"] = session_label
        run = SignalDigestRun(
            workspace_id=workspace_id,
            digest_type=SignalDigestType.SESSION.value,
            status=SignalDigestStatus.PENDING.value,
            digest_version=self.settings.signal_digest_version,
            title="Signal digest pending",
            period_start=request.period_start,
            period_end=request.period_end,
            timezone=timezone,
            filters_json=filters_json,
            summary_json={},
            section_counts_json={},
            warnings_json=[],
        )
        try:
            created_run = await self.repository.create_run(run)
            built = await self.build_digest_payload(
                payload=request,
                filters_json=filters_json,
                max_items=max_items_resolved,
                session_label=session_label,
            )
            created_run.title = built.title
            created_run.summary_json = built.summary_json
            created_run.section_counts_json = built.section_counts_json
            created_run.warnings_json = built.warnings_json
            created_run.status = (
                SignalDigestStatus.COMPLETED_WITH_WARNINGS.value
                if built.warnings_json
                else SignalDigestStatus.COMPLETED.value
            )
            await self.repository.update_run(created_run)
            await self.repository.create_items(
                [
                    draft_item_to_model(
                        draft=draft,
                        workspace_id=workspace_id,
                        digest_run_id=created_run.id,
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
                409,
                "signal_digest_conflict",
                "Signal digest could not be persisted",
            ) from error

    async def validate_workspace(self, workspace_id: UUID) -> None:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")

    async def resolve_scope(self, workspace_id: UUID, filters: SignalDigestFilters) -> DigestScope:
        symbol_ids = [*filters.symbol_ids]
        timeframes = [timeframe.value for timeframe in filters.timeframes]
        is_empty = False
        if filters.watchlist_id is not None:
            watchlist_scope = await self.repository.list_watchlist_scope(
                workspace_id=workspace_id,
                watchlist_id=filters.watchlist_id,
            )
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
        return DigestScope(
            watchlist_id=filters.watchlist_id,
            symbol_ids=symbol_ids,
            timeframes=timeframes,
            is_empty=is_empty,
        )

    async def load_artifacts(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DigestScope,
        session_label: str | None,
        limit: int,
    ) -> SignalDigestArtifacts:
        return SignalDigestArtifacts(
            signals=await self.repository.list_signals(
                workspace_id=workspace_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                session_label=session_label,
                limit=limit,
            ),
            outcomes=await self.repository.list_outcomes(
                workspace_id=workspace_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            news_context=await self.repository.list_news_context(
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
            data_quality_warnings=await self.repository.list_data_quality_warnings(
                workspace_id=workspace_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            stale_memory=await self.repository.list_stale_memory(
                workspace_id=workspace_id,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            quality_reviews=await self.repository.list_quality_reviews(
                workspace_id=workspace_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            readiness_reviews=await self.repository.list_readiness_reviews(
                workspace_id=workspace_id,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
            due_scan_configs=await self.repository.list_due_scan_configs(
                workspace_id=workspace_id,
                period_end=period_end,
                scope=scope,
                limit=limit,
            ),
        )


def digest_filters_json(filters: SignalDigestFilters, max_items: int) -> dict[str, object]:
    payload = filters.model_dump(mode="json", by_alias=True)
    payload["maxItems"] = max_items
    return payload


def draft_item_to_model(
    draft: SignalDigestDraftItem,
    workspace_id: UUID,
    digest_run_id: UUID,
    sort_order: int,
) -> SignalDigestItem:
    return SignalDigestItem(
        workspace_id=workspace_id,
        digest_run_id=digest_run_id,
        item_type=draft.item_type.value,
        symbol_id=draft.symbol_id,
        signal_id=draft.signal_id,
        setup_context_id=draft.setup_context_id,
        analysis_run_id=draft.analysis_run_id,
        outcome_id=draft.outcome_id,
        action_item_id=draft.action_item_id,
        news_event_id=draft.news_event_id,
        priority=draft.priority.value,
        title=draft.title,
        summary=draft.summary,
        tags_json=[str(tag) for tag in draft.tags],
        metadata_json=to_json_value(draft.metadata),
        sort_order=sort_order,
    )


def intersect_or_default[T](current: list[T], candidates: list[T]) -> list[T]:
    if not current:
        return candidates
    candidate_set = set(candidates)
    return [item for item in current if item in candidate_set]
