from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.historical_cases.models import HistoricalCaseSearch, HistoricalCaseVector
from app.modules.signals.models import Signal


class HistoricalCaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_vector_by_signal_id(
        self,
        signal_id: UUID,
        vector_version: str,
    ) -> HistoricalCaseVector | None:
        statement: Select[tuple[HistoricalCaseVector]] = select(HistoricalCaseVector).where(
            HistoricalCaseVector.signal_id == signal_id,
            HistoricalCaseVector.vector_version == vector_version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_vector(
        self,
        vector: HistoricalCaseVector,
        force_recompute: bool,
    ) -> HistoricalCaseVector:
        existing = await self.get_vector_by_signal_id(vector.signal_id, vector.vector_version)
        if existing is None:
            self.session.add(vector)
            await self.session.flush()
            await self.session.refresh(vector)
            return vector
        if not force_recompute:
            return existing
        existing.workspace_id = vector.workspace_id
        existing.analysis_run_id = vector.analysis_run_id
        existing.symbol_id = vector.symbol_id
        existing.timeframe = vector.timeframe
        existing.strategy_profile_key = vector.strategy_profile_key
        existing.strategy_profile_version = vector.strategy_profile_version
        existing.pattern_type = vector.pattern_type
        existing.bias = vector.bias
        existing.classification_status = vector.classification_status
        existing.confidence_score = vector.confidence_score
        existing.vector_json = vector.vector_json
        existing.feature_summary_json = vector.feature_summary_json
        existing.indicator_summary_json = vector.indicator_summary_json
        existing.outcome_summary_json = vector.outcome_summary_json
        existing.metadata_json = vector.metadata_json
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def list_candidate_vectors(
        self,
        workspace_id: UUID,
        vector_version: str,
        limit: int,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        strategy_profile_key: str | None = None,
        pattern_type: str | None = None,
        bias: str | None = None,
        classification_status: str | None = None,
        exclude_signal_id: UUID | None = None,
    ) -> list[HistoricalCaseVector]:
        statement: Select[tuple[HistoricalCaseVector]] = (
            select(HistoricalCaseVector)
            .where(
                HistoricalCaseVector.workspace_id == workspace_id,
                HistoricalCaseVector.vector_version == vector_version,
            )
            .order_by(HistoricalCaseVector.created_at.desc())
            .limit(limit)
        )
        if symbol_id is not None:
            statement = statement.where(HistoricalCaseVector.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(HistoricalCaseVector.timeframe == timeframe)
        if strategy_profile_key is not None:
            statement = statement.where(
                HistoricalCaseVector.strategy_profile_key == strategy_profile_key
            )
        if pattern_type is not None:
            statement = statement.where(HistoricalCaseVector.pattern_type == pattern_type)
        if bias is not None:
            statement = statement.where(HistoricalCaseVector.bias == bias)
        if classification_status is not None:
            statement = statement.where(
                HistoricalCaseVector.classification_status == classification_status
            )
        if exclude_signal_id is not None:
            statement = statement.where(HistoricalCaseVector.signal_id != exclude_signal_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_search(self, search: HistoricalCaseSearch) -> HistoricalCaseSearch:
        self.session.add(search)
        await self.session.flush()
        await self.session.refresh(search)
        return search

    async def list_backfill_signals(
        self,
        workspace_id: UUID,
        vector_version: str,
        limit: int,
        force_recompute: bool,
    ) -> list[Signal]:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(Signal.workspace_id == workspace_id)
            .order_by(Signal.created_at.asc())
            .limit(limit)
        )
        if not force_recompute:
            vector_exists = (
                select(HistoricalCaseVector.id)
                .where(
                    HistoricalCaseVector.signal_id == Signal.id,
                    HistoricalCaseVector.vector_version == vector_version,
                )
                .exists()
            )
            statement = statement.where(~vector_exists)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
