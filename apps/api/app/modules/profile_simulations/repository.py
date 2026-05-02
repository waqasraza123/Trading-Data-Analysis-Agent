from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import AnalysisMode, AnalysisRun
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.outcomes.models import SignalOutcome
from app.modules.patterns.models import PatternCandidate
from app.modules.profile_simulations.models import (
    StrategyProfileSimulationResult,
    StrategyProfileSimulationRun,
)
from app.modules.signals.models import Signal


class ProfileSimulationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(
        self,
        run: StrategyProfileSimulationRun,
    ) -> StrategyProfileSimulationRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run(
        self,
        run: StrategyProfileSimulationRun,
    ) -> StrategyProfileSimulationRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> StrategyProfileSimulationRun | None:
        return await self.session.get(StrategyProfileSimulationRun, run_id)

    async def list_results(
        self,
        run_id: UUID,
        limit: int,
        offset: int,
    ) -> list[StrategyProfileSimulationResult]:
        statement: Select[tuple[StrategyProfileSimulationResult]] = (
            select(StrategyProfileSimulationResult)
            .where(StrategyProfileSimulationResult.simulation_run_id == run_id)
            .order_by(StrategyProfileSimulationResult.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_historical_signals(
        self,
        workspace_id: UUID,
        strategy_profile_key: str,
        limit: int,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        pattern_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[Signal]:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .join(AnalysisRun, AnalysisRun.id == Signal.analysis_run_id)
            .where(
                Signal.workspace_id == workspace_id,
                Signal.strategy_profile_key == strategy_profile_key,
                AnalysisRun.analysis_mode != AnalysisMode.REPLAY,
            )
            .order_by(AnalysisRun.end_time.asc(), Signal.created_at.asc())
            .limit(limit)
        )
        if symbol_id is not None:
            statement = statement.where(Signal.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(Signal.timeframe == timeframe)
        if pattern_type is not None:
            statement = statement.where(Signal.pattern_type == pattern_type)
        if start_time is not None:
            statement = statement.where(AnalysisRun.end_time >= start_time)
        if end_time is not None:
            statement = statement.where(AnalysisRun.end_time <= end_time)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_candidates(self, analysis_run_id: UUID) -> list[PatternCandidate]:
        statement: Select[tuple[PatternCandidate]] = (
            select(PatternCandidate)
            .where(PatternCandidate.analysis_run_id == analysis_run_id)
            .order_by(
                PatternCandidate.is_selected.desc(),
                PatternCandidate.strength_score.desc(),
                PatternCandidate.created_at.desc(),
            )
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_feature_snapshot(self, analysis_run_id: UUID) -> FeatureSnapshot | None:
        statement: Select[tuple[FeatureSnapshot]] = (
            select(FeatureSnapshot)
            .where(FeatureSnapshot.analysis_run_id == analysis_run_id)
            .order_by(FeatureSnapshot.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_indicator_snapshot(self, analysis_run_id: UUID) -> IndicatorSnapshot | None:
        statement: Select[tuple[IndicatorSnapshot]] = (
            select(IndicatorSnapshot)
            .where(IndicatorSnapshot.analysis_run_id == analysis_run_id)
            .order_by(IndicatorSnapshot.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_outcomes(
        self,
        signal_id: UUID,
        horizons_minutes: list[int],
    ) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(
                SignalOutcome.signal_id == signal_id,
                SignalOutcome.horizon_minutes.in_(horizons_minutes),
            )
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_results(
        self,
        results: list[StrategyProfileSimulationResult],
    ) -> list[StrategyProfileSimulationResult]:
        self.session.add_all(results)
        await self.session.flush()
        for result in results:
            await self.session.refresh(result)
        return results
