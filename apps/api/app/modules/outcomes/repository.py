from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import AnalysisMode, AnalysisRun
from app.modules.outcomes.models import OutcomeEvaluationRun, SignalOutcome
from app.modules.signals.models import Signal


class OutcomeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_outcome(
        self,
        signal_id: UUID,
        horizon_minutes: int,
        evaluation_version: str,
    ) -> SignalOutcome | None:
        statement: Select[tuple[SignalOutcome]] = select(SignalOutcome).where(
            SignalOutcome.signal_id == signal_id,
            SignalOutcome.horizon_minutes == horizon_minutes,
            SignalOutcome.evaluation_version == evaluation_version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_outcome_by_horizon(
        self,
        signal_id: UUID,
        horizon_minutes: int,
    ) -> SignalOutcome | None:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(
                SignalOutcome.signal_id == signal_id,
                SignalOutcome.horizon_minutes == horizon_minutes,
            )
            .order_by(SignalOutcome.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_by_signal_id(self, signal_id: UUID) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.signal_id == signal_id)
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_analysis_run_id(self, analysis_run_id: UUID) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.analysis_run_id == analysis_run_id)
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def upsert_outcome(
        self,
        outcome: SignalOutcome,
        force_recompute: bool,
    ) -> SignalOutcome:
        existing = await self.get_outcome(
            signal_id=outcome.signal_id,
            horizon_minutes=outcome.horizon_minutes,
            evaluation_version=outcome.evaluation_version,
        )
        if existing is None:
            self.session.add(outcome)
            await self.session.flush()
            await self.session.refresh(outcome)
            return outcome
        if not force_recompute:
            return existing
        copy_outcome_values(source=outcome, target=existing)
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def delete_for_signal_version(self, signal_id: UUID, evaluation_version: str) -> None:
        await self.session.execute(
            delete(SignalOutcome).where(
                SignalOutcome.signal_id == signal_id,
                SignalOutcome.evaluation_version == evaluation_version,
            )
        )
        await self.session.flush()

    async def create_evaluation_run(self, run: OutcomeEvaluationRun) -> OutcomeEvaluationRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_evaluation_run(self, run_id: UUID) -> OutcomeEvaluationRun | None:
        return await self.session.get(OutcomeEvaluationRun, run_id)

    async def list_backfill_signals(
        self,
        workspace_id: UUID,
        limit: int,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        include_replay: bool = False,
    ) -> list[Signal]:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .join(AnalysisRun, AnalysisRun.id == Signal.analysis_run_id)
            .where(Signal.workspace_id == workspace_id)
            .order_by(Signal.created_at.asc())
            .limit(limit)
        )
        if symbol_id is not None:
            statement = statement.where(Signal.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(Signal.timeframe == timeframe)
        if not include_replay:
            statement = statement.where(AnalysisRun.analysis_mode != AnalysisMode.REPLAY)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_filtered_outcomes(
        self,
        workspace_id: UUID,
        horizon_minutes: int,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        pattern_type: str | None = None,
        strategy_profile_key: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = select(SignalOutcome).where(
            SignalOutcome.workspace_id == workspace_id,
            SignalOutcome.horizon_minutes == horizon_minutes,
        )
        if symbol_id is not None:
            statement = statement.where(SignalOutcome.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(SignalOutcome.timeframe == timeframe)
        if pattern_type is not None:
            statement = statement.where(SignalOutcome.pattern_type == pattern_type)
        if strategy_profile_key is not None:
            statement = statement.where(SignalOutcome.strategy_profile_key == strategy_profile_key)
        if start_time is not None:
            statement = statement.where(SignalOutcome.reference_time >= start_time)
        if end_time is not None:
            statement = statement.where(SignalOutcome.reference_time <= end_time)
        result = await self.session.execute(statement)
        return list(result.scalars().all())


def copy_outcome_values(source: SignalOutcome, target: SignalOutcome) -> None:
    target.workspace_id = source.workspace_id
    target.analysis_run_id = source.analysis_run_id
    target.symbol_id = source.symbol_id
    target.timeframe = source.timeframe
    target.strategy_profile_key = source.strategy_profile_key
    target.strategy_profile_version = source.strategy_profile_version
    target.pattern_type = source.pattern_type
    target.bias = source.bias
    target.classification_status = source.classification_status
    target.evaluation_status = source.evaluation_status
    target.reference_time = source.reference_time
    target.reference_price = source.reference_price
    target.future_window_start = source.future_window_start
    target.future_window_end = source.future_window_end
    target.future_candle_count = source.future_candle_count
    target.max_favorable_move = source.max_favorable_move
    target.max_adverse_move = source.max_adverse_move
    target.net_move = source.net_move
    target.max_favorable_pips = source.max_favorable_pips
    target.max_adverse_pips = source.max_adverse_pips
    target.net_pips = source.net_pips
    target.max_favorable_ticks = source.max_favorable_ticks
    target.max_adverse_ticks = source.max_adverse_ticks
    target.net_ticks = source.net_ticks
    target.direction_followed = source.direction_followed
    target.reversal_detected = source.reversal_detected
    target.outcome_label = source.outcome_label
    target.movement_quality = source.movement_quality
    target.metadata_json = source.metadata_json
