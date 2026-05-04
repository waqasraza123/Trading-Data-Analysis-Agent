from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import AnalysisRun
from app.modules.outcomes.models import SignalOutcome
from app.modules.pattern_attribution.models import (
    PatternAttributionResult,
    PatternAttributionRun,
)
from app.modules.pattern_attribution.schemas import PatternAttributionFilters
from app.modules.patterns.models import PatternCandidate
from app.modules.signals.models import Signal, SignalRiskNote


@dataclass(frozen=True)
class CandidateSignalRow:
    candidate: PatternCandidate
    analysis_run: AnalysisRun
    signal: Signal | None


class PatternAttributionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: PatternAttributionRun) -> PatternAttributionRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run(self, run: PatternAttributionRun) -> PatternAttributionRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: UUID) -> PatternAttributionRun | None:
        return await self.session.get(PatternAttributionRun, run_id)

    async def list_runs(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> list[PatternAttributionRun]:
        statement: Select[tuple[PatternAttributionRun]] = (
            select(PatternAttributionRun)
            .where(PatternAttributionRun.workspace_id == workspace_id)
            .order_by(PatternAttributionRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(PatternAttributionRun.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_candidate_signal_rows(
        self,
        workspace_id: UUID,
        filters: PatternAttributionFilters,
    ) -> list[CandidateSignalRow]:
        statement: Select[tuple[PatternCandidate, AnalysisRun, Signal | None]] = (
            select(PatternCandidate, AnalysisRun, Signal)
            .join(AnalysisRun, AnalysisRun.id == PatternCandidate.analysis_run_id)
            .outerjoin(Signal, Signal.analysis_run_id == PatternCandidate.analysis_run_id)
            .where(PatternCandidate.workspace_id == workspace_id)
            .order_by(AnalysisRun.end_time.desc(), PatternCandidate.created_at.desc())
            .limit(filters.limit)
        )
        if filters.pattern_type is not None:
            statement = statement.where(PatternCandidate.pattern_type == filters.pattern_type)
        if filters.strategy_profile_key is not None:
            statement = statement.where(Signal.strategy_profile_key == filters.strategy_profile_key)
        if filters.symbol_id is not None:
            statement = statement.where(PatternCandidate.symbol_id == filters.symbol_id)
        if filters.timeframe is not None:
            statement = statement.where(AnalysisRun.timeframe == filters.timeframe)
        if filters.start_time is not None:
            statement = statement.where(AnalysisRun.end_time >= filters.start_time)
        if filters.end_time is not None:
            statement = statement.where(AnalysisRun.end_time <= filters.end_time)
        result = await self.session.execute(statement)
        return [
            CandidateSignalRow(candidate=row[0], analysis_run=row[1], signal=row[2])
            for row in result.all()
        ]

    async def list_outcomes_by_signal_ids(
        self,
        signal_ids: list[UUID],
        horizons_minutes: list[int],
    ) -> dict[tuple[UUID, int], SignalOutcome]:
        unique_signal_ids = list({signal_id for signal_id in signal_ids})
        if not unique_signal_ids:
            return {}
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(
                SignalOutcome.signal_id.in_(unique_signal_ids),
                SignalOutcome.horizon_minutes.in_(horizons_minutes),
            )
            .order_by(SignalOutcome.created_at.desc())
        )
        result = await self.session.execute(statement)
        outcomes: dict[tuple[UUID, int], SignalOutcome] = {}
        for outcome in result.scalars().all():
            outcomes.setdefault((outcome.signal_id, outcome.horizon_minutes), outcome)
        return outcomes

    async def list_risk_note_codes_by_signal_ids(
        self,
        signal_ids: list[UUID],
    ) -> dict[UUID, set[str]]:
        unique_signal_ids = list({signal_id for signal_id in signal_ids})
        if not unique_signal_ids:
            return {}
        statement = select(SignalRiskNote.signal_id, SignalRiskNote.code).where(
            SignalRiskNote.signal_id.in_(unique_signal_ids)
        )
        result = await self.session.execute(statement)
        codes: dict[UUID, set[str]] = {}
        for signal_id, code in result.all():
            codes.setdefault(signal_id, set()).add(code)
        return codes

    async def create_results(
        self,
        results: list[PatternAttributionResult],
    ) -> list[PatternAttributionResult]:
        self.session.add_all(results)
        await self.session.flush()
        return results

    async def list_results(
        self,
        run_id: UUID,
        limit: int,
        offset: int,
        attribution_label: str | None = None,
        pattern_type: str | None = None,
    ) -> list[PatternAttributionResult]:
        statement: Select[tuple[PatternAttributionResult]] = (
            select(PatternAttributionResult)
            .where(PatternAttributionResult.attribution_run_id == run_id)
            .order_by(
                PatternAttributionResult.horizon_minutes.asc(),
                PatternAttributionResult.pattern_type.asc(),
                PatternAttributionResult.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        if attribution_label is not None:
            statement = statement.where(
                PatternAttributionResult.attribution_label == attribution_label
            )
        if pattern_type is not None:
            statement = statement.where(PatternAttributionResult.pattern_type == pattern_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
