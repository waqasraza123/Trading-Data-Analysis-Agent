from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cohort_drift.models import CohortDriftResult, CohortDriftRun
from app.modules.cohort_drift.schemas import CohortDriftFilters
from app.modules.market_regimes.models import MarketRegimeContext
from app.modules.market_sessions.models import MarketSessionContext
from app.modules.outcomes.models import SignalOutcome
from app.modules.signals.models import Signal


@dataclass(frozen=True)
class CohortDriftOutcomeRow:
    signal_id: UUID
    horizon_minutes: int
    reference_time: datetime
    strategy_profile_key: str | None
    pattern_type: str | None
    symbol_id: UUID
    timeframe: str
    bias: str
    classification_status: str
    confidence_score: Decimal
    confidence_label: str
    evaluation_status: str
    outcome_label: str
    market_session_label: str | None
    market_regime_label: str | None


class CohortDriftRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: CohortDriftRun) -> CohortDriftRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run(self, run: CohortDriftRun) -> CohortDriftRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> CohortDriftRun | None:
        return await self.session.get(CohortDriftRun, run_id)

    async def list_runs(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> list[CohortDriftRun]:
        statement: Select[tuple[CohortDriftRun]] = (
            select(CohortDriftRun)
            .where(CohortDriftRun.workspace_id == workspace_id)
            .order_by(CohortDriftRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(CohortDriftRun.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_results(self, results: list[CohortDriftResult]) -> list[CohortDriftResult]:
        self.session.add_all(results)
        await self.session.flush()
        for result in results:
            await self.session.refresh(result)
        return results

    async def list_results(
        self,
        drift_run_id: UUID,
        limit: int,
        offset: int,
        drift_label: str | None = None,
        severity: str | None = None,
        horizon_minutes: int | None = None,
        cohort_key: str | None = None,
    ) -> list[CohortDriftResult]:
        statement: Select[tuple[CohortDriftResult]] = (
            select(CohortDriftResult)
            .where(CohortDriftResult.drift_run_id == drift_run_id)
            .order_by(
                CohortDriftResult.drift_score.desc(),
                CohortDriftResult.horizon_minutes.asc(),
                CohortDriftResult.cohort_key.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        statement = apply_result_filters(
            statement,
            drift_label,
            severity,
            horizon_minutes,
            cohort_key,
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_recent_results(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        drift_label: str | None = None,
        severity: str | None = None,
        horizon_minutes: int | None = None,
        cohort_key: str | None = None,
    ) -> list[CohortDriftResult]:
        statement: Select[tuple[CohortDriftResult]] = (
            select(CohortDriftResult)
            .join(CohortDriftRun, CohortDriftRun.id == CohortDriftResult.drift_run_id)
            .where(CohortDriftResult.workspace_id == workspace_id)
            .order_by(
                CohortDriftRun.created_at.desc(),
                CohortDriftResult.drift_score.desc(),
                CohortDriftResult.cohort_key.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        statement = apply_result_filters(
            statement,
            drift_label,
            severity,
            horizon_minutes,
            cohort_key,
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_outcome_rows(
        self,
        workspace_id: UUID,
        horizons_minutes: list[int],
        filters: CohortDriftFilters,
        start_time: datetime,
        end_time: datetime,
    ) -> list[CohortDriftOutcomeRow]:
        session_label = (
            select(MarketSessionContext.session_label)
            .where(MarketSessionContext.signal_id == Signal.id)
            .order_by(MarketSessionContext.created_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        regime_trend = (
            select(MarketRegimeContext.trend_regime)
            .where(MarketRegimeContext.signal_id == Signal.id)
            .order_by(MarketRegimeContext.created_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        regime_volatility = (
            select(MarketRegimeContext.volatility_regime)
            .where(MarketRegimeContext.signal_id == Signal.id)
            .order_by(MarketRegimeContext.created_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        regime_range = (
            select(MarketRegimeContext.range_regime)
            .where(MarketRegimeContext.signal_id == Signal.id)
            .order_by(MarketRegimeContext.created_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        statement = (
            select(
                Signal.id,
                SignalOutcome.horizon_minutes,
                SignalOutcome.reference_time,
                SignalOutcome.strategy_profile_key,
                SignalOutcome.pattern_type,
                SignalOutcome.symbol_id,
                SignalOutcome.timeframe,
                SignalOutcome.bias,
                SignalOutcome.classification_status,
                Signal.confidence_score,
                Signal.confidence_label,
                SignalOutcome.evaluation_status,
                SignalOutcome.outcome_label,
                session_label,
                regime_trend,
                regime_volatility,
                regime_range,
            )
            .join(SignalOutcome, SignalOutcome.signal_id == Signal.id)
            .where(
                Signal.workspace_id == workspace_id,
                SignalOutcome.workspace_id == workspace_id,
                SignalOutcome.horizon_minutes.in_(horizons_minutes),
                SignalOutcome.reference_time >= start_time,
                SignalOutcome.reference_time < end_time,
            )
            .order_by(SignalOutcome.reference_time.asc(), SignalOutcome.created_at.asc())
            .limit(filters.max_outcomes)
        )
        statement = apply_source_filters(statement, filters)
        result = await self.session.execute(statement)
        return [
            CohortDriftOutcomeRow(
                signal_id=row[0],
                horizon_minutes=row[1],
                reference_time=row[2],
                strategy_profile_key=row[3],
                pattern_type=row[4],
                symbol_id=row[5],
                timeframe=row[6],
                bias=row[7],
                classification_status=row[8],
                confidence_score=row[9],
                confidence_label=row[10],
                evaluation_status=row[11],
                outcome_label=row[12],
                market_session_label=row[13],
                market_regime_label=market_regime_label(row[14], row[15], row[16]),
            )
            for row in result.all()
        ]


def apply_source_filters(
    statement: Select[object],
    filters: CohortDriftFilters,
) -> Select[object]:
    if filters.strategy_profile_key is not None:
        statement = statement.where(
            SignalOutcome.strategy_profile_key == filters.strategy_profile_key
        )
    if filters.symbol_id is not None:
        statement = statement.where(SignalOutcome.symbol_id == filters.symbol_id)
    if filters.timeframe is not None:
        statement = statement.where(SignalOutcome.timeframe == filters.timeframe)
    if filters.pattern_type is not None:
        statement = statement.where(SignalOutcome.pattern_type == filters.pattern_type)
    if filters.bias is not None:
        statement = statement.where(SignalOutcome.bias == filters.bias)
    if filters.confidence_label is not None:
        statement = statement.where(Signal.confidence_label == filters.confidence_label)
    return statement


def apply_result_filters(
    statement: Select[object],
    drift_label: str | None,
    severity: str | None,
    horizon_minutes: int | None,
    cohort_key: str | None,
) -> Select[object]:
    if drift_label is not None:
        statement = statement.where(CohortDriftResult.drift_label == drift_label)
    if severity is not None:
        statement = statement.where(CohortDriftResult.severity == severity)
    if horizon_minutes is not None:
        statement = statement.where(CohortDriftResult.horizon_minutes == horizon_minutes)
    if cohort_key is not None:
        statement = statement.where(CohortDriftResult.cohort_key == cohort_key)
    return statement


def market_regime_label(
    trend_regime: str | None,
    volatility_regime: str | None,
    range_regime: str | None,
) -> str | None:
    if trend_regime is None and volatility_regime is None and range_regime is None:
        return None
    return "/".join(
        [
            trend_regime or "unknown_trend",
            volatility_regime or "unknown_volatility",
            range_regime or "unknown_range",
        ]
    )
