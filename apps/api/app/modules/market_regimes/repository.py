from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.market_regimes.models import MarketRegimeContext


class MarketRegimeContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        regime_version: str | None = None,
    ) -> MarketRegimeContext | None:
        statement: Select[tuple[MarketRegimeContext]] = select(MarketRegimeContext).where(
            MarketRegimeContext.analysis_run_id == analysis_run_id
        )
        if regime_version is not None:
            statement = statement.where(MarketRegimeContext.regime_version == regime_version)
        statement = statement.order_by(MarketRegimeContext.created_at.desc())
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_by_signal_id(
        self,
        signal_id: UUID,
        regime_version: str | None = None,
    ) -> MarketRegimeContext | None:
        statement: Select[tuple[MarketRegimeContext]] = select(MarketRegimeContext).where(
            MarketRegimeContext.signal_id == signal_id
        )
        if regime_version is not None:
            statement = statement.where(MarketRegimeContext.regime_version == regime_version)
        statement = statement.order_by(MarketRegimeContext.created_at.desc())
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def upsert_for_analysis_run(
        self,
        context: MarketRegimeContext,
        force_recompute: bool,
    ) -> MarketRegimeContext:
        existing = await self.get_by_analysis_run_id(
            context.analysis_run_id,
            context.regime_version,
        )
        if existing is None:
            self.session.add(context)
            await self.session.flush()
            await self.session.refresh(context)
            return context
        if not force_recompute:
            return existing
        existing.signal_id = context.signal_id
        existing.trend_regime = context.trend_regime
        existing.volatility_regime = context.volatility_regime
        existing.range_regime = context.range_regime
        existing.liquidity_regime = context.liquidity_regime
        existing.data_quality_label = context.data_quality_label
        existing.confidence_score = context.confidence_score
        existing.confidence_label = context.confidence_label
        existing.summary = context.summary
        existing.feature_inputs_json = context.feature_inputs_json
        existing.indicator_inputs_json = context.indicator_inputs_json
        existing.warnings_json = context.warnings_json
        existing.metadata_json = context.metadata_json
        await self.session.flush()
        await self.session.refresh(existing)
        return existing
