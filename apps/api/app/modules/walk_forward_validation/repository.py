from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.outcomes.models import SignalOutcome
from app.modules.signals.models import Signal
from app.modules.walk_forward_validation.models import (
    WalkForwardValidationComparison,
    WalkForwardValidationRun,
    WalkForwardValidationWindow,
)
from app.modules.walk_forward_validation.schemas import WalkForwardValidationFilters


@dataclass(frozen=True)
class WalkForwardOutcomeRow:
    signal_id: UUID
    horizon_minutes: int
    reference_time: datetime
    bias: str
    classification_status: str
    evaluation_status: str
    outcome_label: str
    confidence_score: Decimal


@dataclass(frozen=True)
class WalkForwardSourceBounds:
    start_time: datetime | None
    end_time: datetime | None


class WalkForwardValidationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: WalkForwardValidationRun) -> WalkForwardValidationRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run(self, run: WalkForwardValidationRun) -> WalkForwardValidationRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> WalkForwardValidationRun | None:
        return await self.session.get(WalkForwardValidationRun, run_id)

    async def list_runs(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> list[WalkForwardValidationRun]:
        statement: Select[tuple[WalkForwardValidationRun]] = (
            select(WalkForwardValidationRun)
            .where(WalkForwardValidationRun.workspace_id == workspace_id)
            .order_by(WalkForwardValidationRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(WalkForwardValidationRun.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_windows(
        self,
        windows: list[WalkForwardValidationWindow],
    ) -> list[WalkForwardValidationWindow]:
        self.session.add_all(windows)
        await self.session.flush()
        for window in windows:
            await self.session.refresh(window)
        return windows

    async def create_comparisons(
        self,
        comparisons: list[WalkForwardValidationComparison],
    ) -> list[WalkForwardValidationComparison]:
        self.session.add_all(comparisons)
        await self.session.flush()
        for comparison in comparisons:
            await self.session.refresh(comparison)
        return comparisons

    async def list_windows(
        self,
        validation_run_id: UUID,
        limit: int,
        offset: int,
        horizon_minutes: int | None = None,
        stability_label: str | None = None,
    ) -> list[WalkForwardValidationWindow]:
        statement: Select[tuple[WalkForwardValidationWindow]] = (
            select(WalkForwardValidationWindow)
            .where(WalkForwardValidationWindow.validation_run_id == validation_run_id)
            .order_by(
                WalkForwardValidationWindow.window_index.asc(),
                WalkForwardValidationWindow.horizon_minutes.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        if horizon_minutes is not None:
            statement = statement.where(WalkForwardValidationWindow.horizon_minutes == horizon_minutes)
        if stability_label is not None:
            statement = statement.where(WalkForwardValidationWindow.stability_label == stability_label)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_comparisons(
        self,
        validation_run_id: UUID,
    ) -> list[WalkForwardValidationComparison]:
        statement: Select[tuple[WalkForwardValidationComparison]] = (
            select(WalkForwardValidationComparison)
            .where(WalkForwardValidationComparison.validation_run_id == validation_run_id)
            .order_by(WalkForwardValidationComparison.horizon_minutes.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def source_bounds(
        self,
        workspace_id: UUID,
        horizons_minutes: list[int],
        filters: WalkForwardValidationFilters,
    ) -> WalkForwardSourceBounds:
        statement = (
            select(
                func.min(SignalOutcome.reference_time),
                func.max(SignalOutcome.reference_time),
            )
            .join(Signal, Signal.id == SignalOutcome.signal_id)
            .where(
                Signal.workspace_id == workspace_id,
                SignalOutcome.workspace_id == workspace_id,
                SignalOutcome.horizon_minutes.in_(horizons_minutes),
            )
        )
        statement = apply_source_filters(statement, filters, include_time_filters=True)
        result = await self.session.execute(statement)
        row = result.one()
        return WalkForwardSourceBounds(start_time=row[0], end_time=row[1])

    async def list_outcome_rows(
        self,
        workspace_id: UUID,
        horizons_minutes: list[int],
        filters: WalkForwardValidationFilters,
        start_time: datetime,
        end_time: datetime,
    ) -> list[WalkForwardOutcomeRow]:
        candidate_statement = (
            select(Signal.id)
            .join(SignalOutcome, SignalOutcome.signal_id == Signal.id)
            .where(
                Signal.workspace_id == workspace_id,
                SignalOutcome.workspace_id == workspace_id,
                SignalOutcome.horizon_minutes.in_(horizons_minutes),
                SignalOutcome.reference_time >= start_time,
                SignalOutcome.reference_time <= end_time,
            )
            .group_by(Signal.id)
            .order_by(func.min(SignalOutcome.reference_time).asc(), Signal.id.asc())
            .limit(filters.max_signals)
        )
        candidate_statement = apply_source_filters(
            candidate_statement,
            filters,
            include_time_filters=False,
        ).subquery()
        statement = (
            select(
                Signal.id,
                SignalOutcome.horizon_minutes,
                SignalOutcome.reference_time,
                SignalOutcome.bias,
                SignalOutcome.classification_status,
                SignalOutcome.evaluation_status,
                SignalOutcome.outcome_label,
                Signal.confidence_score,
            )
            .join(SignalOutcome, SignalOutcome.signal_id == Signal.id)
            .where(
                Signal.id.in_(select(candidate_statement.c.id)),
                SignalOutcome.horizon_minutes.in_(horizons_minutes),
                SignalOutcome.reference_time >= start_time,
                SignalOutcome.reference_time <= end_time,
            )
            .order_by(
                SignalOutcome.reference_time.asc(),
                SignalOutcome.horizon_minutes.asc(),
                SignalOutcome.created_at.asc(),
            )
        )
        statement = apply_source_filters(statement, filters, include_time_filters=False)
        result = await self.session.execute(statement)
        return [
            WalkForwardOutcomeRow(
                signal_id=row[0],
                horizon_minutes=row[1],
                reference_time=row[2],
                bias=row[3],
                classification_status=row[4],
                evaluation_status=row[5],
                outcome_label=row[6],
                confidence_score=row[7],
            )
            for row in result.all()
        ]


def apply_source_filters(
    statement: Select[object],
    filters: WalkForwardValidationFilters,
    include_time_filters: bool,
) -> Select[object]:
    if filters.strategy_profile_key is not None:
        statement = statement.where(SignalOutcome.strategy_profile_key == filters.strategy_profile_key)
    if filters.pattern_type is not None:
        statement = statement.where(SignalOutcome.pattern_type == filters.pattern_type)
    if filters.symbol_id is not None:
        statement = statement.where(SignalOutcome.symbol_id == filters.symbol_id)
    if filters.timeframe is not None:
        statement = statement.where(SignalOutcome.timeframe == filters.timeframe)
    if include_time_filters and filters.start_time is not None:
        statement = statement.where(SignalOutcome.reference_time >= filters.start_time)
    if include_time_filters and filters.end_time is not None:
        statement = statement.where(SignalOutcome.reference_time <= filters.end_time)
    return statement
