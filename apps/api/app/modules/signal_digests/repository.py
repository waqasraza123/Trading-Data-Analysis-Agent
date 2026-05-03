from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_plans.models import ReasoningActionItem
from app.modules.data_quality.models import DataQualityRun
from app.modules.decision_readiness.models import DecisionReadinessAssessment
from app.modules.intelligence_quality.models import IntelligenceQualityRun
from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.market_scans.models import (
    MarketWatchlist,
    MarketWatchlistItem,
    ScheduledScanConfig,
)
from app.modules.market_sessions.models import MarketSessionContext
from app.modules.news.models import NewsEvent, SignalNewsCorrelation
from app.modules.outcomes.models import SignalOutcome
from app.modules.setup_context.models import SetupContext
from app.modules.signal_digests.models import SignalDigestItem, SignalDigestRun
from app.modules.signals.models import Signal, SignalEvidence, SignalRiskNote
from app.modules.symbols.models import Symbol


@dataclass(frozen=True)
class DigestScope:
    watchlist_id: UUID | None
    symbol_ids: list[UUID]
    timeframes: list[str]
    is_empty: bool = False


@dataclass(frozen=True)
class SignalDigestSignalContext:
    signal: Signal
    symbol: Symbol
    evidence_count: int
    risk_count: int
    setup_context_id: UUID | None = None


@dataclass(frozen=True)
class SignalDigestOutcomeContext:
    outcome: SignalOutcome
    symbol: Symbol
    signal: Signal | None


@dataclass(frozen=True)
class SignalDigestNewsContext:
    correlation: SignalNewsCorrelation
    event: NewsEvent
    symbol: Symbol | None
    signal: Signal | None


@dataclass(frozen=True)
class SignalDigestActionContext:
    action_item: ReasoningActionItem
    symbol: Symbol | None
    signal: Signal | None


@dataclass(frozen=True)
class SignalDigestDataQualityContext:
    run: DataQualityRun
    symbol: Symbol | None


@dataclass(frozen=True)
class SignalDigestMemoryContext:
    snapshot: RollingMarketStateSnapshot
    symbol: Symbol


@dataclass(frozen=True)
class SignalDigestQualityContext:
    quality_run: IntelligenceQualityRun
    symbol: Symbol | None
    signal: Signal | None


@dataclass(frozen=True)
class SignalDigestReadinessContext:
    assessment: DecisionReadinessAssessment
    symbol: Symbol | None
    signal: Signal | None


@dataclass(frozen=True)
class SignalDigestScheduledScanContext:
    scan_config: ScheduledScanConfig
    watchlist: MarketWatchlist | None
    symbol: Symbol | None


class SignalDigestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: SignalDigestRun) -> SignalDigestRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run(self, run: SignalDigestRun) -> SignalDigestRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def create_items(self, items: list[SignalDigestItem]) -> list[SignalDigestItem]:
        self.session.add_all(items)
        await self.session.flush()
        for item in items:
            await self.session.refresh(item)
        return items

    async def get_run(self, digest_id: UUID) -> SignalDigestRun | None:
        return await self.session.get(SignalDigestRun, digest_id)

    async def list_runs(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        digest_type: str | None = None,
        status: str | None = None,
    ) -> list[SignalDigestRun]:
        statement: Select[tuple[SignalDigestRun]] = (
            select(SignalDigestRun)
            .where(SignalDigestRun.workspace_id == workspace_id)
            .order_by(SignalDigestRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if digest_type is not None:
            statement = statement.where(SignalDigestRun.digest_type == digest_type)
        if status is not None:
            statement = statement.where(SignalDigestRun.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_items(
        self,
        digest_id: UUID,
        limit: int,
        offset: int,
        item_type: str | None = None,
    ) -> list[SignalDigestItem]:
        statement: Select[tuple[SignalDigestItem]] = (
            select(SignalDigestItem)
            .where(SignalDigestItem.digest_run_id == digest_id)
            .order_by(SignalDigestItem.sort_order.asc(), SignalDigestItem.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        if item_type is not None:
            statement = statement.where(SignalDigestItem.item_type == item_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_watchlist_scope(
        self,
        workspace_id: UUID,
        watchlist_id: UUID,
    ) -> list[tuple[UUID, str]]:
        statement = select(MarketWatchlistItem.symbol_id, MarketWatchlistItem.timeframe).where(
            MarketWatchlistItem.workspace_id == workspace_id,
            MarketWatchlistItem.watchlist_id == watchlist_id,
            MarketWatchlistItem.is_active.is_(True),
        )
        result = await self.session.execute(statement)
        return [(row.symbol_id, row.timeframe) for row in result]

    async def list_signals(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DigestScope,
        session_label: str | None,
        limit: int,
    ) -> list[SignalDigestSignalContext]:
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
        if session_label is not None:
            statement = statement.join(
                MarketSessionContext,
                MarketSessionContext.signal_id == Signal.id,
            ).where(MarketSessionContext.session_label == session_label)
        result = await self.session.execute(statement)
        rows = result.all()
        signals = [row[0] for row in rows]
        signal_ids = [signal.id for signal in signals]
        evidence_counts = await self.count_evidence_by_signal(signal_ids)
        risk_counts = await self.count_risk_notes_by_signal(signal_ids)
        setup_context_ids = await self.latest_setup_context_ids_by_signal(signal_ids)
        return [
            SignalDigestSignalContext(
                signal=row[0],
                symbol=row[1],
                evidence_count=evidence_counts.get(row[0].id, 0),
                risk_count=risk_counts.get(row[0].id, 0),
                setup_context_id=setup_context_ids.get(row[0].id),
            )
            for row in rows
        ]

    async def latest_setup_context_ids_by_signal(
        self,
        signal_ids: list[UUID],
    ) -> dict[UUID, UUID]:
        if not signal_ids:
            return {}
        statement = (
            select(SetupContext.signal_id, SetupContext.id)
            .where(SetupContext.signal_id.in_(signal_ids))
            .order_by(SetupContext.signal_id.asc(), SetupContext.created_at.desc())
        )
        result = await self.session.execute(statement)
        latest_by_signal: dict[UUID, UUID] = {}
        for row in result:
            latest_by_signal.setdefault(row.signal_id, row.id)
        return latest_by_signal

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

    async def list_outcomes(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DigestScope,
        limit: int,
    ) -> list[SignalDigestOutcomeContext]:
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
            SignalDigestOutcomeContext(outcome=row[0], symbol=row[1], signal=row[2])
            for row in result.all()
        ]

    async def list_news_context(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DigestScope,
        limit: int,
    ) -> list[SignalDigestNewsContext]:
        statement: Select[tuple[SignalNewsCorrelation, NewsEvent, Symbol | None, Signal | None]] = (
            select(SignalNewsCorrelation, NewsEvent, Symbol, Signal)
            .join(NewsEvent, NewsEvent.id == SignalNewsCorrelation.news_event_id)
            .outerjoin(Signal, Signal.id == SignalNewsCorrelation.signal_id)
            .outerjoin(Symbol, Symbol.id == Signal.symbol_id)
            .where(
                SignalNewsCorrelation.workspace_id == workspace_id,
                NewsEvent.event_time >= period_start,
                NewsEvent.event_time <= period_end,
                SignalNewsCorrelation.correlation_label.in_(["possible", "strong"]),
            )
            .order_by(SignalNewsCorrelation.correlation_score.desc(), NewsEvent.event_time.desc())
            .limit(limit)
        )
        statement = apply_correlation_scope(statement, scope)
        result = await self.session.execute(statement)
        return [
            SignalDigestNewsContext(correlation=row[0], event=row[1], symbol=row[2], signal=row[3])
            for row in result.all()
        ]

    async def list_pending_actions(
        self,
        workspace_id: UUID,
        period_end: datetime,
        scope: DigestScope,
        limit: int,
    ) -> list[SignalDigestActionContext]:
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
            SignalDigestActionContext(action_item=row[0], symbol=row[1], signal=row[2])
            for row in result.all()
        ]

    async def list_data_quality_warnings(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DigestScope,
        limit: int,
    ) -> list[SignalDigestDataQualityContext]:
        statement: Select[tuple[DataQualityRun, Symbol | None]] = (
            select(DataQualityRun, Symbol)
            .outerjoin(Symbol, Symbol.id == DataQualityRun.symbol_id)
            .where(
                DataQualityRun.workspace_id == workspace_id,
                DataQualityRun.created_at >= period_start,
                DataQualityRun.created_at <= period_end,
                DataQualityRun.quality_label.in_(["degraded", "poor", "insufficient_data"]),
            )
            .order_by(DataQualityRun.created_at.desc())
            .limit(limit)
        )
        statement = apply_data_quality_scope(statement, scope)
        result = await self.session.execute(statement)
        return [SignalDigestDataQualityContext(run=row[0], symbol=row[1]) for row in result.all()]

    async def list_stale_memory(
        self,
        workspace_id: UUID,
        period_end: datetime,
        scope: DigestScope,
        limit: int,
    ) -> list[SignalDigestMemoryContext]:
        statement: Select[tuple[RollingMarketStateSnapshot, Symbol]] = (
            select(RollingMarketStateSnapshot, Symbol)
            .join(Symbol, Symbol.id == RollingMarketStateSnapshot.symbol_id)
            .where(
                RollingMarketStateSnapshot.workspace_id == workspace_id,
                RollingMarketStateSnapshot.updated_at <= period_end,
                or_(
                    RollingMarketStateSnapshot.freshness_label.in_(["stale", "delayed", "no_data"]),
                    RollingMarketStateSnapshot.data_quality_label.in_(
                        ["degraded", "poor", "insufficient", "unknown"]
                    ),
                ),
            )
            .order_by(
                RollingMarketStateSnapshot.updated_at.desc(),
                RollingMarketStateSnapshot.created_at.desc(),
            )
            .limit(limit)
        )
        statement = apply_memory_scope(statement, scope)
        result = await self.session.execute(statement)
        return [SignalDigestMemoryContext(snapshot=row[0], symbol=row[1]) for row in result.all()]

    async def list_quality_reviews(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DigestScope,
        limit: int,
    ) -> list[SignalDigestQualityContext]:
        statement: Select[tuple[IntelligenceQualityRun, Symbol | None, Signal | None]] = (
            select(IntelligenceQualityRun, Symbol, Signal)
            .outerjoin(Signal, Signal.id == IntelligenceQualityRun.signal_id)
            .outerjoin(Symbol, Symbol.id == Signal.symbol_id)
            .where(
                IntelligenceQualityRun.workspace_id == workspace_id,
                IntelligenceQualityRun.created_at >= period_start,
                IntelligenceQualityRun.created_at <= period_end,
                IntelligenceQualityRun.quality_label.in_(
                    ["review_recommended", "inconsistent", "insufficient_context"]
                ),
            )
            .order_by(IntelligenceQualityRun.created_at.desc())
            .limit(limit)
        )
        statement = apply_quality_scope(statement, scope)
        result = await self.session.execute(statement)
        return [
            SignalDigestQualityContext(quality_run=row[0], symbol=row[1], signal=row[2])
            for row in result.all()
        ]

    async def list_readiness_reviews(
        self,
        workspace_id: UUID,
        period_start: datetime,
        period_end: datetime,
        scope: DigestScope,
        limit: int,
    ) -> list[SignalDigestReadinessContext]:
        statement: Select[tuple[DecisionReadinessAssessment, Symbol | None, Signal | None]] = (
            select(DecisionReadinessAssessment, Symbol, Signal)
            .outerjoin(Signal, Signal.id == DecisionReadinessAssessment.signal_id)
            .outerjoin(Symbol, Symbol.id == Signal.symbol_id)
            .where(
                DecisionReadinessAssessment.workspace_id == workspace_id,
                DecisionReadinessAssessment.created_at >= period_start,
                DecisionReadinessAssessment.created_at <= period_end,
                DecisionReadinessAssessment.readiness_label.in_(
                    ["review_recommended", "blocked", "insufficient_context"]
                ),
            )
            .order_by(DecisionReadinessAssessment.created_at.desc())
            .limit(limit)
        )
        statement = apply_readiness_scope(statement, scope)
        result = await self.session.execute(statement)
        return [
            SignalDigestReadinessContext(assessment=row[0], symbol=row[1], signal=row[2])
            for row in result.all()
        ]

    async def list_due_scan_configs(
        self,
        workspace_id: UUID,
        period_end: datetime,
        scope: DigestScope,
        limit: int,
    ) -> list[SignalDigestScheduledScanContext]:
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
        if scope.watchlist_id is not None:
            if scope.is_empty:
                statement = statement.where(false())
                result = await self.session.execute(statement)
                return [
                    SignalDigestScheduledScanContext(
                        scan_config=row[0],
                        watchlist=row[1],
                        symbol=row[2],
                    )
                    for row in result.all()
                ]
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
            SignalDigestScheduledScanContext(scan_config=row[0], watchlist=row[1], symbol=row[2])
            for row in result.all()
        ]


def apply_signal_scope(
    statement: Select[tuple[Signal, Symbol]],
    scope: DigestScope,
) -> Select[tuple[Signal, Symbol]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(Signal.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(Signal.timeframe.in_(scope.timeframes))
    return statement


def apply_outcome_scope(
    statement: Select[tuple[SignalOutcome, Symbol, Signal | None]],
    scope: DigestScope,
) -> Select[tuple[SignalOutcome, Symbol, Signal | None]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(SignalOutcome.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(SignalOutcome.timeframe.in_(scope.timeframes))
    return statement


def apply_correlation_scope(
    statement: Select[tuple[SignalNewsCorrelation, NewsEvent, Symbol | None, Signal | None]],
    scope: DigestScope,
) -> Select[tuple[SignalNewsCorrelation, NewsEvent, Symbol | None, Signal | None]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(Signal.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(Signal.timeframe.in_(scope.timeframes))
    return statement


def apply_action_scope(
    statement: Select[tuple[ReasoningActionItem, Symbol | None, Signal | None]],
    scope: DigestScope,
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


def apply_data_quality_scope(
    statement: Select[tuple[DataQualityRun, Symbol | None]],
    scope: DigestScope,
) -> Select[tuple[DataQualityRun, Symbol | None]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(DataQualityRun.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(DataQualityRun.timeframe.in_(scope.timeframes))
    return statement


def apply_memory_scope(
    statement: Select[tuple[RollingMarketStateSnapshot, Symbol]],
    scope: DigestScope,
) -> Select[tuple[RollingMarketStateSnapshot, Symbol]]:
    if scope.is_empty:
        return statement.where(false())
    if scope.symbol_ids:
        statement = statement.where(RollingMarketStateSnapshot.symbol_id.in_(scope.symbol_ids))
    if scope.timeframes:
        statement = statement.where(RollingMarketStateSnapshot.timeframe.in_(scope.timeframes))
    return statement


def apply_quality_scope(
    statement: Select[tuple[IntelligenceQualityRun, Symbol | None, Signal | None]],
    scope: DigestScope,
) -> Select[tuple[IntelligenceQualityRun, Symbol | None, Signal | None]]:
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


def apply_readiness_scope(
    statement: Select[tuple[DecisionReadinessAssessment, Symbol | None, Signal | None]],
    scope: DigestScope,
) -> Select[tuple[DecisionReadinessAssessment, Symbol | None, Signal | None]]:
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
