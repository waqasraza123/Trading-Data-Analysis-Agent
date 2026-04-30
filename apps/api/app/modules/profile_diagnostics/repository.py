from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.outcomes.models import SignalOutcome
from app.modules.profile_diagnostics.models import (
    CalibrationRecommendation,
    PatternOutcomeDiagnostic,
    StrategyProfileDiagnostic,
    StrategyProfileDiagnosticRun,
)
from app.modules.signals.models import Signal


@dataclass(frozen=True)
class OutcomeSignalRow:
    outcome: SignalOutcome
    confidence_score: Decimal | None
    candidate_strength: Decimal | None


class ProfileDiagnosticRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(
        self,
        run: StrategyProfileDiagnosticRun,
    ) -> StrategyProfileDiagnosticRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> StrategyProfileDiagnosticRun | None:
        return await self.session.get(StrategyProfileDiagnosticRun, run_id)

    async def update_run(
        self,
        run: StrategyProfileDiagnosticRun,
    ) -> StrategyProfileDiagnosticRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def list_outcome_signal_rows(
        self,
        workspace_id: UUID,
        horizons_minutes: list[int],
        limit: int,
        strategy_profile_key: str | None = None,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        pattern_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[OutcomeSignalRow]:
        statement = (
            select(SignalOutcome, Signal.confidence_score, Signal.candidate_strength)
            .join(Signal, Signal.id == SignalOutcome.signal_id)
            .where(
                SignalOutcome.workspace_id == workspace_id,
                SignalOutcome.horizon_minutes.in_(horizons_minutes),
            )
            .order_by(SignalOutcome.reference_time.desc(), SignalOutcome.created_at.desc())
            .limit(limit)
        )
        if strategy_profile_key is not None:
            statement = statement.where(SignalOutcome.strategy_profile_key == strategy_profile_key)
        if symbol_id is not None:
            statement = statement.where(SignalOutcome.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(SignalOutcome.timeframe == timeframe)
        if pattern_type is not None:
            statement = statement.where(SignalOutcome.pattern_type == pattern_type)
        if start_time is not None:
            statement = statement.where(SignalOutcome.reference_time >= start_time)
        if end_time is not None:
            statement = statement.where(SignalOutcome.reference_time <= end_time)
        result = await self.session.execute(statement)
        return [
            OutcomeSignalRow(
                outcome=row[0],
                confidence_score=row[1],
                candidate_strength=row[2],
            )
            for row in result.all()
        ]

    async def create_strategy_profile_diagnostics(
        self,
        diagnostics: list[StrategyProfileDiagnostic],
    ) -> list[StrategyProfileDiagnostic]:
        self.session.add_all(diagnostics)
        await self.session.flush()
        return diagnostics

    async def create_pattern_diagnostics(
        self,
        diagnostics: list[PatternOutcomeDiagnostic],
    ) -> list[PatternOutcomeDiagnostic]:
        self.session.add_all(diagnostics)
        await self.session.flush()
        return diagnostics

    async def create_recommendations(
        self,
        recommendations: list[CalibrationRecommendation],
    ) -> list[CalibrationRecommendation]:
        self.session.add_all(recommendations)
        await self.session.flush()
        return recommendations

    async def list_strategy_profile_diagnostics(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        diagnostic_run_id: UUID | None = None,
        strategy_profile_key: str | None = None,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        horizon_minutes: int | None = None,
        diagnostic_label: str | None = None,
    ) -> list[StrategyProfileDiagnostic]:
        statement: Select[tuple[StrategyProfileDiagnostic]] = (
            select(StrategyProfileDiagnostic)
            .where(StrategyProfileDiagnostic.workspace_id == workspace_id)
            .order_by(StrategyProfileDiagnostic.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if diagnostic_run_id is not None:
            statement = statement.where(
                StrategyProfileDiagnostic.diagnostic_run_id == diagnostic_run_id
            )
        if strategy_profile_key is not None:
            statement = statement.where(
                StrategyProfileDiagnostic.strategy_profile_key == strategy_profile_key
            )
        if symbol_id is not None:
            statement = statement.where(StrategyProfileDiagnostic.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(StrategyProfileDiagnostic.timeframe == timeframe)
        if horizon_minutes is not None:
            statement = statement.where(
                StrategyProfileDiagnostic.horizon_minutes == horizon_minutes
            )
        if diagnostic_label is not None:
            statement = statement.where(
                StrategyProfileDiagnostic.diagnostic_label == diagnostic_label
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_pattern_diagnostics(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        diagnostic_run_id: UUID | None = None,
        pattern_type: str | None = None,
        strategy_profile_key: str | None = None,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        horizon_minutes: int | None = None,
        diagnostic_label: str | None = None,
    ) -> list[PatternOutcomeDiagnostic]:
        statement: Select[tuple[PatternOutcomeDiagnostic]] = (
            select(PatternOutcomeDiagnostic)
            .where(PatternOutcomeDiagnostic.workspace_id == workspace_id)
            .order_by(PatternOutcomeDiagnostic.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if diagnostic_run_id is not None:
            statement = statement.where(
                PatternOutcomeDiagnostic.diagnostic_run_id == diagnostic_run_id
            )
        if pattern_type is not None:
            statement = statement.where(PatternOutcomeDiagnostic.pattern_type == pattern_type)
        if strategy_profile_key is not None:
            statement = statement.where(
                PatternOutcomeDiagnostic.strategy_profile_key == strategy_profile_key
            )
        if symbol_id is not None:
            statement = statement.where(PatternOutcomeDiagnostic.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(PatternOutcomeDiagnostic.timeframe == timeframe)
        if horizon_minutes is not None:
            statement = statement.where(PatternOutcomeDiagnostic.horizon_minutes == horizon_minutes)
        if diagnostic_label is not None:
            statement = statement.where(
                PatternOutcomeDiagnostic.diagnostic_label == diagnostic_label
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_recommendations(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        diagnostic_run_id: UUID | None = None,
        status: str | None = None,
        severity: str | None = None,
        recommendation_type: str | None = None,
        strategy_profile_key: str | None = None,
        pattern_type: str | None = None,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
    ) -> list[CalibrationRecommendation]:
        statement: Select[tuple[CalibrationRecommendation]] = (
            select(CalibrationRecommendation)
            .where(CalibrationRecommendation.workspace_id == workspace_id)
            .order_by(CalibrationRecommendation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if diagnostic_run_id is not None:
            statement = statement.where(
                CalibrationRecommendation.diagnostic_run_id == diagnostic_run_id
            )
        if status is not None:
            statement = statement.where(CalibrationRecommendation.status == status)
        if severity is not None:
            statement = statement.where(CalibrationRecommendation.severity == severity)
        if recommendation_type is not None:
            statement = statement.where(
                CalibrationRecommendation.recommendation_type == recommendation_type
            )
        if strategy_profile_key is not None:
            statement = statement.where(
                CalibrationRecommendation.strategy_profile_key == strategy_profile_key
            )
        if pattern_type is not None:
            statement = statement.where(CalibrationRecommendation.pattern_type == pattern_type)
        if symbol_id is not None:
            statement = statement.where(CalibrationRecommendation.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(CalibrationRecommendation.timeframe == timeframe)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_recommendation(
        self,
        recommendation_id: UUID,
    ) -> CalibrationRecommendation | None:
        return await self.session.get(CalibrationRecommendation, recommendation_id)

    async def update_recommendation(
        self,
        recommendation: CalibrationRecommendation,
    ) -> CalibrationRecommendation:
        await self.session.flush()
        await self.session.refresh(recommendation)
        return recommendation
