from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_plans.models import ReasoningActionItem
from app.modules.candles.models import Candle
from app.modules.cross_asset_context.models import CrossAssetContextRun
from app.modules.daily_briefs.models import DailyBriefItem, DailyBriefRun
from app.modules.data_quality.models import DataQualityRun
from app.modules.decision_readiness.models import DecisionReadinessAssessment
from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.market_regimes.models import MarketRegimeContext
from app.modules.market_scans.models import (
    MarketWatchlist,
    MarketWatchlistItem,
    ScheduledScanConfig,
)
from app.modules.market_sessions.models import MarketSessionContext
from app.modules.outcomes.models import SignalOutcome
from app.modules.setup_context.models import SetupContext
from app.modules.signal_digests.models import SignalDigestItem, SignalDigestRun
from app.modules.signal_priority.models import SignalPriorityScore
from app.modules.signals.models import Signal, SignalEvidence, SignalRiskNote
from app.modules.symbols.models import Symbol
from app.modules.timeframe_aggregation.models import MultiTimeframeContext
from app.modules.trading_journal.models import JournalEntry


@dataclass(frozen=True)
class DailyBriefScope:
    watchlist_id: UUID | None
    symbol_ids: list[UUID]
    timeframes: list[str]
    is_empty: bool = False


@dataclass(frozen=True)
class DailyBriefSignalContext:
    signal: Signal
    symbol: Symbol
    evidence_count: int
    risk_count: int
    setup_context: SetupContext | None = None
    priority_score: SignalPriorityScore | None = None
    readiness: DecisionReadinessAssessment | None = None
    memory: RollingMarketStateSnapshot | None = None


@dataclass(frozen=True)
class DailyBriefOutcomeContext:
    outcome: SignalOutcome
    symbol: Symbol
    signal: Signal | None


@dataclass(frozen=True)
class DailyBriefActionContext:
    action_item: ReasoningActionItem
    symbol: Symbol | None
    signal: Signal | None


@dataclass(frozen=True)
class DailyBriefMemoryContext:
    snapshot: RollingMarketStateSnapshot
    symbol: Symbol


@dataclass(frozen=True)
class DailyBriefProviderHealthContext:
    status: str
    freshness_label: str
    latest_final_candle_time: datetime | None
    missing_candle_count: int
    stale_seconds: int | None
    summary: str
    symbol_id: UUID | None
    symbol: str | None
    timeframe: str | None
    source_id: UUID | None
    provider: str | None
    snapshot_id: UUID


@dataclass(frozen=True)
class DailyBriefDataQualityContext:
    run: DataQualityRun
    symbol: Symbol | None


@dataclass(frozen=True)
class DailyBriefMarketContext:
    source_type: str
    source_id: UUID
    symbol_id: UUID | None
    symbol: str | None
    timeframe: str | None
    label: str
    summary: str
    metadata: dict[str, object]
    created_at: datetime
    signal_id: UUID | None = None
    analysis_run_id: UUID | None = None


@dataclass(frozen=True)
class DailyBriefScanContext:
    scan_config: ScheduledScanConfig
    watchlist: MarketWatchlist | None
    symbol: Symbol | None


@dataclass(frozen=True)
class DailyBriefJournalContext:
    entry: JournalEntry
    symbol: Symbol | None
    signal: Signal | None


@dataclass(frozen=True)
class DailyBriefLatestCandleContext:
    symbol_id: UUID
    symbol: str | None
    timeframe: str
    latest_final_candle_time: datetime


@dataclass(frozen=True)
class DailyBriefDigestContext:
    digest: SignalDigestRun
    items: list[SignalDigestItem]


class DailyBriefRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: DailyBriefRun) -> DailyBriefRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run(self, run: DailyBriefRun) -> DailyBriefRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def create_items(self, items: list[DailyBriefItem]) -> list[DailyBriefItem]:
        self.session.add_all(items)
        await self.session.flush()
        for item in items:
            await self.session.refresh(item)
        return items

    async def get_run(self, brief_id: UUID) -> DailyBriefRun | None:
        return await self.session.get(DailyBriefRun, brief_id)

    async def list_runs(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        brief_type: str | None = None,
        status: str | None = None,
        watchlist_id: UUID | None = None,
    ) -> list[DailyBriefRun]:
        statement: Select[tuple[DailyBriefRun]] = (
            select(DailyBriefRun)
            .where(DailyBriefRun.workspace_id == workspace_id)
            .order_by(DailyBriefRun.generated_at.desc(), DailyBriefRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if brief_type is not None:
            statement = statement.where(DailyBriefRun.brief_type == brief_type)
        if status is not None:
            statement = statement.where(DailyBriefRun.status == status)
        if watchlist_id is not None:
            statement = statement.where(DailyBriefRun.watchlist_id == watchlist_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_latest_run(
        self,
        workspace_id: UUID,
        brief_type: str | None = None,
        watchlist_id: UUID | None = None,
    ) -> DailyBriefRun | None:
        statement: Select[tuple[DailyBriefRun]] = (
            select(DailyBriefRun)
            .where(DailyBriefRun.workspace_id == workspace_id)
            .order_by(DailyBriefRun.generated_at.desc(), DailyBriefRun.created_at.desc())
            .limit(1)
        )
        if brief_type is not None:
            statement = statement.where(DailyBriefRun.brief_type == brief_type)
        if watchlist_id is not None:
            statement = statement.where(DailyBriefRun.watchlist_id == watchlist_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_items(
        self,
        brief_id: UUID,
        limit: int,
        offset: int,
        item_type: str | None = None,
        priority: str | None = None,
    ) -> list[DailyBriefItem]:
        statement: Select[tuple[DailyBriefItem]] = (
            select(DailyBriefItem)
            .where(DailyBriefItem.brief_run_id == brief_id)
            .order_by(DailyBriefItem.sort_order.asc(), DailyBriefItem.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        if item_type is not None:
            statement = statement.where(DailyBriefItem.item_type == item_type)
        if priority is not None:
            statement = statement.where(DailyBriefItem.priority == priority)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_watchlist_scope(
        self, workspace_id: UUID, watchlist_id: UUID
    ) -> list[tuple[UUID, str]]:
        statement = select(MarketWatchlistItem.symbol_id, MarketWatchlistItem.timeframe).where(
            MarketWatchlistItem.workspace_id == workspace_id,
            MarketWatchlistItem.watchlist_id == watchlist_id,
            MarketWatchlistItem.is_active.is_(True),
        )
        result = await self.session.execute(statement)
        return [(row.symbol_id, row.timeframe) for row in result]

    async def get_latest_signal_digest(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DailyBriefScope,
    ) -> DailyBriefDigestContext | None:
        statement: Select[tuple[SignalDigestRun]] = (
            select(SignalDigestRun)
            .where(
                SignalDigestRun.workspace_id == workspace_id,
                SignalDigestRun.status.in_(["completed", "completed_with_warnings"]),
                SignalDigestRun.period_start <= period_end,
                SignalDigestRun.period_end >= period_start,
            )
            .order_by(SignalDigestRun.created_at.desc())
            .limit(1)
        )
        if scope.watchlist_id is not None:
            statement = statement.where(
                or_(
                    SignalDigestRun.digest_type == "watchlist",
                    SignalDigestRun.filters_json["watchlist_id"].astext == str(scope.watchlist_id),
                )
            )
        result = await self.session.execute(statement)
        digest = result.scalar_one_or_none()
        if digest is None:
            return None
        items_statement = (
            select(SignalDigestItem)
            .where(SignalDigestItem.digest_run_id == digest.id)
            .order_by(SignalDigestItem.sort_order.asc(), SignalDigestItem.created_at.asc())
            .limit(50)
        )
        items_result = await self.session.execute(items_statement)
        return DailyBriefDigestContext(digest=digest, items=list(items_result.scalars().all()))

    async def list_priority_signals(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefSignalContext]:
        statement: Select[tuple[SignalPriorityScore, Signal, Symbol]] = (
            select(SignalPriorityScore, Signal, Symbol)
            .join(Signal, Signal.id == SignalPriorityScore.signal_id)
            .join(Symbol, Symbol.id == SignalPriorityScore.symbol_id)
            .where(
                SignalPriorityScore.workspace_id == workspace_id,
                Signal.created_at >= period_start,
                Signal.created_at <= period_end,
            )
            .order_by(SignalPriorityScore.priority_score.desc(), Signal.created_at.desc())
            .limit(limit)
        )
        statement = apply_priority_scope(statement, scope)
        result = await self.session.execute(statement)
        rows = result.all()
        signal_ids = [row[1].id for row in rows]
        setup_contexts = await self.latest_setup_context_by_signal(signal_ids)
        readiness = await self.latest_readiness_by_signal(signal_ids)
        memories = await self.latest_memory_by_signal(signal_ids)
        evidence_counts = await self.count_evidence_by_signal(signal_ids)
        risk_counts = await self.count_risk_notes_by_signal(signal_ids)
        return [
            DailyBriefSignalContext(
                signal=row[1],
                symbol=row[2],
                evidence_count=evidence_counts.get(row[1].id, 0),
                risk_count=risk_counts.get(row[1].id, 0),
                setup_context=setup_contexts.get(row[1].id),
                priority_score=row[0],
                readiness=readiness.get(row[1].id),
                memory=memories.get(row[1].id),
            )
            for row in rows
        ]

    async def list_recent_signals(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefSignalContext]:
        statement: Select[tuple[Signal, Symbol]] = (
            select(Signal, Symbol)
            .join(Symbol, Symbol.id == Signal.symbol_id)
            .where(
                Signal.workspace_id == workspace_id,
                Signal.created_at >= period_start,
                Signal.created_at <= period_end,
            )
            .order_by(Signal.created_at.desc())
            .limit(limit)
        )
        statement = apply_signal_scope(statement, scope)
        result = await self.session.execute(statement)
        rows = result.all()
        signal_ids = [row[0].id for row in rows]
        setup_contexts = await self.latest_setup_context_by_signal(signal_ids)
        priorities = await self.latest_priority_by_signal(signal_ids)
        readiness = await self.latest_readiness_by_signal(signal_ids)
        memories = await self.latest_memory_by_signal(signal_ids)
        evidence_counts = await self.count_evidence_by_signal(signal_ids)
        risk_counts = await self.count_risk_notes_by_signal(signal_ids)
        return [
            DailyBriefSignalContext(
                signal=row[0],
                symbol=row[1],
                evidence_count=evidence_counts.get(row[0].id, 0),
                risk_count=risk_counts.get(row[0].id, 0),
                setup_context=setup_contexts.get(row[0].id),
                priority_score=priorities.get(row[0].id),
                readiness=readiness.get(row[0].id),
                memory=memories.get(row[0].id),
            )
            for row in rows
        ]

    async def latest_setup_context_by_signal(
        self, signal_ids: list[UUID]
    ) -> dict[UUID, SetupContext]:
        if not signal_ids:
            return {}
        statement = (
            select(SetupContext)
            .where(SetupContext.signal_id.in_(signal_ids))
            .order_by(SetupContext.signal_id.asc(), SetupContext.created_at.desc())
        )
        result = await self.session.execute(statement)
        contexts: dict[UUID, SetupContext] = {}
        for context in result.scalars().all():
            contexts.setdefault(context.signal_id, context)
        return contexts

    async def latest_priority_by_signal(
        self, signal_ids: list[UUID]
    ) -> dict[UUID, SignalPriorityScore]:
        if not signal_ids:
            return {}
        statement = (
            select(SignalPriorityScore)
            .where(SignalPriorityScore.signal_id.in_(signal_ids))
            .order_by(SignalPriorityScore.signal_id.asc(), SignalPriorityScore.created_at.desc())
        )
        result = await self.session.execute(statement)
        scores: dict[UUID, SignalPriorityScore] = {}
        for score in result.scalars().all():
            scores.setdefault(score.signal_id, score)
        return scores

    async def latest_readiness_by_signal(
        self, signal_ids: list[UUID]
    ) -> dict[UUID, DecisionReadinessAssessment]:
        if not signal_ids:
            return {}
        statement = (
            select(DecisionReadinessAssessment)
            .where(DecisionReadinessAssessment.signal_id.in_(signal_ids))
            .order_by(
                DecisionReadinessAssessment.signal_id.asc(),
                DecisionReadinessAssessment.created_at.desc(),
            )
        )
        result = await self.session.execute(statement)
        assessments: dict[UUID, DecisionReadinessAssessment] = {}
        for assessment in result.scalars().all():
            if assessment.signal_id is not None:
                assessments.setdefault(assessment.signal_id, assessment)
        return assessments

    async def latest_memory_by_signal(
        self, signal_ids: list[UUID]
    ) -> dict[UUID, RollingMarketStateSnapshot]:
        if not signal_ids:
            return {}
        statement = (
            select(RollingMarketStateSnapshot)
            .where(RollingMarketStateSnapshot.latest_signal_id.in_(signal_ids))
            .order_by(
                RollingMarketStateSnapshot.latest_signal_id.asc(),
                RollingMarketStateSnapshot.updated_at.desc(),
            )
        )
        result = await self.session.execute(statement)
        snapshots: dict[UUID, RollingMarketStateSnapshot] = {}
        for snapshot in result.scalars().all():
            if snapshot.latest_signal_id is not None:
                snapshots.setdefault(snapshot.latest_signal_id, snapshot)
        return snapshots

    async def count_evidence_by_signal(self, signal_ids: list[UUID]) -> dict[UUID, int]:
        if not signal_ids:
            return {}
        statement = select(SignalEvidence.signal_id).where(SignalEvidence.signal_id.in_(signal_ids))
        result = await self.session.execute(statement)
        counts: dict[UUID, int] = {}
        for row in result:
            counts[row.signal_id] = counts.get(row.signal_id, 0) + 1
        return counts

    async def count_risk_notes_by_signal(self, signal_ids: list[UUID]) -> dict[UUID, int]:
        if not signal_ids:
            return {}
        statement = select(SignalRiskNote.signal_id).where(SignalRiskNote.signal_id.in_(signal_ids))
        result = await self.session.execute(statement)
        counts: dict[UUID, int] = {}
        for row in result:
            counts[row.signal_id] = counts.get(row.signal_id, 0) + 1
        return counts

    async def list_memory_contexts(
        self,
        workspace_id: UUID,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefMemoryContext]:
        statement: Select[tuple[RollingMarketStateSnapshot, Symbol]] = (
            select(RollingMarketStateSnapshot, Symbol)
            .join(Symbol, Symbol.id == RollingMarketStateSnapshot.symbol_id)
            .where(
                RollingMarketStateSnapshot.workspace_id == workspace_id,
                RollingMarketStateSnapshot.updated_at <= period_end,
            )
            .order_by(RollingMarketStateSnapshot.updated_at.desc())
            .limit(limit)
        )
        statement = apply_memory_scope(statement, scope)
        result = await self.session.execute(statement)
        return [DailyBriefMemoryContext(snapshot=row[0], symbol=row[1]) for row in result.all()]

    async def list_provider_health_contexts(
        self,
        workspace_id: UUID,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefProviderHealthContext]:
        from app.modules.provider_health.models import ProviderHealthSnapshot

        statement = (
            select(ProviderHealthSnapshot, Symbol)
            .outerjoin(Symbol, Symbol.id == ProviderHealthSnapshot.symbol_id)
            .where(
                ProviderHealthSnapshot.workspace_id == workspace_id,
                ProviderHealthSnapshot.created_at <= period_end,
            )
            .order_by(ProviderHealthSnapshot.updated_at.desc())
            .limit(limit)
        )
        statement = apply_provider_scope(statement, scope)
        result = await self.session.execute(statement)
        return [
            DailyBriefProviderHealthContext(
                status=row[0].status,
                freshness_label=row[0].freshness_label,
                latest_final_candle_time=row[0].latest_final_candle_time,
                missing_candle_count=row[0].missing_candle_count,
                stale_seconds=row[0].stale_seconds,
                summary=row[0].summary,
                symbol_id=row[0].symbol_id,
                symbol=row[1].symbol if row[1] is not None else None,
                timeframe=row[0].timeframe,
                source_id=row[0].source_id,
                provider=row[0].provider,
                snapshot_id=row[0].id,
            )
            for row in result.all()
        ]

    async def list_latest_final_candles(
        self,
        workspace_id: UUID,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefLatestCandleContext]:
        statement = (
            select(Candle.symbol_id, Symbol.symbol, Candle.timeframe, func.max(Candle.timestamp))
            .join(Symbol, Symbol.id == Candle.symbol_id)
            .where(
                Candle.workspace_id == workspace_id,
                Candle.timestamp <= period_end,
                Candle.is_final.is_(True),
            )
            .group_by(Candle.symbol_id, Symbol.symbol, Candle.timeframe)
            .order_by(func.max(Candle.timestamp).desc())
            .limit(limit)
        )
        if scope.is_empty:
            statement = statement.where(false())
        if scope.symbol_ids:
            statement = statement.where(Candle.symbol_id.in_(scope.symbol_ids))
        if scope.timeframes:
            statement = statement.where(Candle.timeframe.in_(scope.timeframes))
        result = await self.session.execute(statement)
        return [
            DailyBriefLatestCandleContext(
                symbol_id=row[0],
                symbol=row[1],
                timeframe=row[2],
                latest_final_candle_time=row[3],
            )
            for row in result.all()
        ]

    async def list_data_quality_contexts(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefDataQualityContext]:
        statement: Select[tuple[DataQualityRun, Symbol | None]] = (
            select(DataQualityRun, Symbol)
            .outerjoin(Symbol, Symbol.id == DataQualityRun.symbol_id)
            .where(
                DataQualityRun.workspace_id == workspace_id,
                DataQualityRun.created_at >= period_start,
                DataQualityRun.created_at <= period_end,
            )
            .order_by(DataQualityRun.created_at.desc())
            .limit(limit)
        )
        statement = apply_data_quality_scope(statement, scope)
        result = await self.session.execute(statement)
        return [DailyBriefDataQualityContext(run=row[0], symbol=row[1]) for row in result.all()]

    async def list_outcome_contexts(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefOutcomeContext]:
        statement: Select[tuple[SignalOutcome, Symbol, Signal | None]] = (
            select(SignalOutcome, Symbol, Signal)
            .join(Symbol, Symbol.id == SignalOutcome.symbol_id)
            .outerjoin(Signal, Signal.id == SignalOutcome.signal_id)
            .where(
                SignalOutcome.workspace_id == workspace_id,
                SignalOutcome.created_at >= period_start,
                SignalOutcome.created_at <= period_end,
            )
            .order_by(SignalOutcome.created_at.desc())
            .limit(limit)
        )
        statement = apply_outcome_scope(statement, scope)
        result = await self.session.execute(statement)
        return [
            DailyBriefOutcomeContext(outcome=row[0], symbol=row[1], signal=row[2])
            for row in result.all()
        ]

    async def list_pending_actions(
        self,
        workspace_id: UUID,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefActionContext]:
        statement: Select[tuple[ReasoningActionItem, Symbol | None, Signal | None]] = (
            select(ReasoningActionItem, Symbol, Signal)
            .outerjoin(Signal, Signal.id == ReasoningActionItem.signal_id)
            .outerjoin(Symbol, Symbol.id == Signal.symbol_id)
            .where(
                ReasoningActionItem.workspace_id == workspace_id,
                ReasoningActionItem.status.in_(["pending", "due", "failed"]),
                or_(ReasoningActionItem.due_at.is_(None), ReasoningActionItem.due_at <= period_end),
            )
            .order_by(
                ReasoningActionItem.due_at.asc().nulls_last(),
                ReasoningActionItem.created_at.asc(),
            )
            .limit(limit)
        )
        statement = apply_action_scope(statement, scope)
        result = await self.session.execute(statement)
        return [
            DailyBriefActionContext(action_item=row[0], symbol=row[1], signal=row[2])
            for row in result.all()
        ]

    async def list_due_scan_contexts(
        self,
        workspace_id: UUID,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefScanContext]:
        statement: Select[tuple[ScheduledScanConfig, MarketWatchlist | None, Symbol | None]] = (
            select(ScheduledScanConfig, MarketWatchlist, Symbol)
            .outerjoin(MarketWatchlist, MarketWatchlist.id == ScheduledScanConfig.watchlist_id)
            .outerjoin(Symbol, Symbol.id == ScheduledScanConfig.symbol_id)
            .where(
                ScheduledScanConfig.workspace_id == workspace_id,
                ScheduledScanConfig.status == "active",
                ScheduledScanConfig.next_run_at.is_not(None),
                ScheduledScanConfig.next_run_at <= period_end,
            )
            .order_by(ScheduledScanConfig.next_run_at.asc())
            .limit(limit)
        )
        if scope.is_empty:
            statement = statement.where(false())
        if scope.watchlist_id is not None:
            statement = statement.where(
                or_(
                    ScheduledScanConfig.watchlist_id == scope.watchlist_id,
                    ScheduledScanConfig.scan_mode == "single_symbol",
                )
            )
        if scope.symbol_ids:
            statement = statement.where(
                or_(
                    ScheduledScanConfig.symbol_id.in_(scope.symbol_ids),
                    ScheduledScanConfig.scan_mode == "watchlist",
                )
            )
        if scope.timeframes:
            statement = statement.where(
                or_(
                    ScheduledScanConfig.timeframe.in_(scope.timeframes),
                    ScheduledScanConfig.scan_mode == "watchlist",
                )
            )
        result = await self.session.execute(statement)
        return [
            DailyBriefScanContext(scan_config=row[0], watchlist=row[1], symbol=row[2])
            for row in result.all()
        ]

    async def list_market_contexts(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefMarketContext]:
        contexts: list[DailyBriefMarketContext] = []
        contexts.extend(
            await self.list_regime_contexts(workspace_id, period_start, period_end, scope, limit)
        )
        contexts.extend(
            await self.list_session_contexts(workspace_id, period_start, period_end, scope, limit)
        )
        contexts.extend(
            await self.list_multi_timeframe_contexts(
                workspace_id, period_start, period_end, scope, limit
            )
        )
        contexts.extend(
            await self.list_cross_asset_contexts(
                workspace_id, period_start, period_end, scope, limit
            )
        )
        return sorted(contexts, key=lambda context: context.created_at, reverse=True)[:limit]

    async def list_regime_contexts(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefMarketContext]:
        statement = (
            select(MarketRegimeContext, Symbol)
            .join(Symbol, Symbol.id == MarketRegimeContext.symbol_id)
            .where(
                MarketRegimeContext.workspace_id == workspace_id,
                MarketRegimeContext.created_at >= period_start,
                MarketRegimeContext.created_at <= period_end,
            )
            .order_by(MarketRegimeContext.created_at.desc())
            .limit(limit)
        )
        statement = apply_regime_scope(statement, scope)
        result = await self.session.execute(statement)
        return [
            DailyBriefMarketContext(
                source_type="market_regime",
                source_id=row[0].id,
                symbol_id=row[0].symbol_id,
                symbol=row[1].symbol,
                timeframe=row[0].timeframe,
                label=row[0].trend_regime,
                summary=row[0].summary,
                metadata={
                    "trendRegime": row[0].trend_regime,
                    "volatilityRegime": row[0].volatility_regime,
                    "rangeRegime": row[0].range_regime,
                    "confidenceLabel": row[0].confidence_label,
                    "dataQualityLabel": row[0].data_quality_label,
                },
                created_at=row[0].created_at,
                signal_id=row[0].signal_id,
                analysis_run_id=row[0].analysis_run_id,
            )
            for row in result.all()
        ]

    async def list_session_contexts(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefMarketContext]:
        statement = (
            select(MarketSessionContext, Symbol)
            .join(Symbol, Symbol.id == MarketSessionContext.symbol_id)
            .where(
                MarketSessionContext.workspace_id == workspace_id,
                MarketSessionContext.context_time >= period_start,
                MarketSessionContext.context_time <= period_end,
            )
            .order_by(MarketSessionContext.context_time.desc())
            .limit(limit)
        )
        statement = apply_session_scope(statement, scope)
        result = await self.session.execute(statement)
        return [
            DailyBriefMarketContext(
                source_type="market_session",
                source_id=row[0].id,
                symbol_id=row[0].symbol_id,
                symbol=row[1].symbol,
                timeframe=row[0].timeframe,
                label=row[0].session_label,
                summary=f"{row[1].symbol} session context is {row[0].session_label}.",
                metadata={
                    "sessionLabel": row[0].session_label,
                    "confidenceScore": row[0].confidence_score,
                },
                created_at=row[0].created_at,
                signal_id=row[0].signal_id,
                analysis_run_id=row[0].analysis_run_id,
            )
            for row in result.all()
        ]

    async def list_multi_timeframe_contexts(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefMarketContext]:
        statement = (
            select(MultiTimeframeContext, Symbol)
            .join(Symbol, Symbol.id == MultiTimeframeContext.symbol_id)
            .where(
                MultiTimeframeContext.workspace_id == workspace_id,
                MultiTimeframeContext.created_at >= period_start,
                MultiTimeframeContext.created_at <= period_end,
            )
            .order_by(MultiTimeframeContext.created_at.desc())
            .limit(limit)
        )
        statement = apply_multi_timeframe_scope(statement, scope)
        result = await self.session.execute(statement)
        return [
            DailyBriefMarketContext(
                source_type="multi_timeframe_context",
                source_id=row[0].id,
                symbol_id=row[0].symbol_id,
                symbol=row[1].symbol,
                timeframe=row[0].primary_timeframe,
                label=row[0].agreement_label,
                summary=row[0].context_summary,
                metadata={
                    "agreementLabel": row[0].agreement_label,
                    "trendAlignment": row[0].trend_alignment,
                    "volatilityAlignment": row[0].volatility_alignment,
                    "rangeAlignment": row[0].range_alignment,
                    "warnings": row[0].warnings_json,
                },
                created_at=row[0].created_at,
                signal_id=row[0].signal_id,
                analysis_run_id=row[0].analysis_run_id,
            )
            for row in result.all()
        ]

    async def list_cross_asset_contexts(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefMarketContext]:
        statement = (
            select(CrossAssetContextRun, Symbol)
            .join(Symbol, Symbol.id == CrossAssetContextRun.base_symbol_id)
            .where(
                CrossAssetContextRun.workspace_id == workspace_id,
                CrossAssetContextRun.created_at >= period_start,
                CrossAssetContextRun.created_at <= period_end,
            )
            .order_by(CrossAssetContextRun.created_at.desc())
            .limit(limit)
        )
        statement = apply_cross_asset_scope(statement, scope)
        result = await self.session.execute(statement)
        return [
            DailyBriefMarketContext(
                source_type="cross_asset_context",
                source_id=row[0].id,
                symbol_id=row[0].base_symbol_id,
                symbol=row[1].symbol,
                timeframe=row[0].timeframe,
                label=row[0].status,
                summary=row[0].summary,
                metadata={
                    "status": row[0].status,
                    "comparedSymbolCount": row[0].compared_symbol_count,
                    "resultCount": row[0].result_count,
                },
                created_at=row[0].created_at,
                signal_id=row[0].signal_id,
                analysis_run_id=row[0].analysis_run_id,
            )
            for row in result.all()
        ]

    async def list_journal_contexts(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DailyBriefScope,
        limit: int,
    ) -> list[DailyBriefJournalContext]:
        statement: Select[tuple[JournalEntry, Symbol | None, Signal | None]] = (
            select(JournalEntry, Symbol, Signal)
            .outerjoin(Signal, Signal.id == JournalEntry.signal_id)
            .outerjoin(Symbol, Symbol.id == Signal.symbol_id)
            .where(
                JournalEntry.workspace_id == workspace_id,
                JournalEntry.created_at >= period_start,
                JournalEntry.created_at <= period_end,
                JournalEntry.status != "archived",
            )
            .order_by(JournalEntry.created_at.desc())
            .limit(limit)
        )
        statement = apply_journal_scope(statement, scope)
        result = await self.session.execute(statement)
        return [
            DailyBriefJournalContext(entry=row[0], symbol=row[1], signal=row[2])
            for row in result.all()
        ]


def apply_priority_scope(
    statement: Select[tuple[SignalPriorityScore, Signal, Symbol]],
    scope: DailyBriefScope,
) -> Select[tuple[SignalPriorityScore, Signal, Symbol]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(SignalPriorityScore.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(SignalPriorityScore.timeframe.in_(scope.timeframes))
    return statement


def apply_signal_scope(
    statement: Select[tuple[Signal, Symbol]],
    scope: DailyBriefScope,
) -> Select[tuple[Signal, Symbol]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(Signal.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(Signal.timeframe.in_(scope.timeframes))
    return statement


def apply_memory_scope(
    statement: Select[tuple[RollingMarketStateSnapshot, Symbol]],
    scope: DailyBriefScope,
) -> Select[tuple[RollingMarketStateSnapshot, Symbol]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(RollingMarketStateSnapshot.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(RollingMarketStateSnapshot.timeframe.in_(scope.timeframes))
    return statement


def apply_provider_scope(
    statement: Select[tuple[object, Symbol]], scope: DailyBriefScope
) -> Select[tuple[object, Symbol]]:
    from app.modules.provider_health.models import ProviderHealthSnapshot

    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(ProviderHealthSnapshot.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(ProviderHealthSnapshot.timeframe.in_(scope.timeframes))
    return statement


def apply_data_quality_scope(
    statement: Select[tuple[DataQualityRun, Symbol | None]],
    scope: DailyBriefScope,
) -> Select[tuple[DataQualityRun, Symbol | None]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(DataQualityRun.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(DataQualityRun.timeframe.in_(scope.timeframes))
    return statement


def apply_outcome_scope(
    statement: Select[tuple[SignalOutcome, Symbol, Signal | None]],
    scope: DailyBriefScope,
) -> Select[tuple[SignalOutcome, Symbol, Signal | None]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(SignalOutcome.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(SignalOutcome.timeframe.in_(scope.timeframes))
    return statement


def apply_action_scope(
    statement: Select[tuple[ReasoningActionItem, Symbol | None, Signal | None]],
    scope: DailyBriefScope,
) -> Select[tuple[ReasoningActionItem, Symbol | None, Signal | None]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(
            or_(Signal.symbol_id.in_(scope.symbol_ids), Signal.id.is_(None))
        )
    if scope.timeframes:
        statement = statement.where(
            or_(Signal.timeframe.in_(scope.timeframes), Signal.id.is_(None))
        )
    return statement


def apply_regime_scope(
    statement: Select[tuple[MarketRegimeContext, Symbol]], scope: DailyBriefScope
) -> Select[tuple[MarketRegimeContext, Symbol]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(MarketRegimeContext.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(MarketRegimeContext.timeframe.in_(scope.timeframes))
    return statement


def apply_session_scope(
    statement: Select[tuple[MarketSessionContext, Symbol]], scope: DailyBriefScope
) -> Select[tuple[MarketSessionContext, Symbol]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(MarketSessionContext.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(MarketSessionContext.timeframe.in_(scope.timeframes))
    return statement


def apply_multi_timeframe_scope(
    statement: Select[tuple[MultiTimeframeContext, Symbol]], scope: DailyBriefScope
) -> Select[tuple[MultiTimeframeContext, Symbol]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(MultiTimeframeContext.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(MultiTimeframeContext.primary_timeframe.in_(scope.timeframes))
    return statement


def apply_cross_asset_scope(
    statement: Select[tuple[CrossAssetContextRun, Symbol]], scope: DailyBriefScope
) -> Select[tuple[CrossAssetContextRun, Symbol]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(CrossAssetContextRun.base_symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(CrossAssetContextRun.timeframe.in_(scope.timeframes))
    return statement


def apply_journal_scope(
    statement: Select[tuple[JournalEntry, Symbol | None, Signal | None]],
    scope: DailyBriefScope,
) -> Select[tuple[JournalEntry, Symbol | None, Signal | None]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(
            or_(Signal.symbol_id.in_(scope.symbol_ids), Signal.id.is_(None))
        )
    if scope.timeframes:
        statement = statement.where(
            or_(Signal.timeframe.in_(scope.timeframes), Signal.id.is_(None))
        )
    return statement
