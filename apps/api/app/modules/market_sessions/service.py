from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.models import AnalysisRun
from app.modules.market_sessions.models import MarketSessionContext, MarketSessionLabel
from app.modules.market_sessions.repository import MarketSessionRepository
from app.modules.signals.models import Signal


class MarketSessionService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = MarketSessionRepository(session)

    async def create_for_analysis_run(self, analysis_run_id: UUID) -> MarketSessionContext:
        run = await self.session.get(AnalysisRun, analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        context = await self.repository.create(
            MarketSessionContext(
                workspace_id=run.workspace_id,
                analysis_run_id=run.id,
                signal_id=None,
                symbol_id=run.symbol_id,
                timeframe=run.timeframe,
                context_time=run.end_time,
                timezone_name=self.settings.market_session_default_timezone,
                session_version=self.settings.market_session_version,
                session_label=session_label(run.end_time).value,
                confidence_score=Decimal("1.0000"),
                context_json={"source": "analysis_run_window", "hourUtc": run.end_time.hour},
            )
        )
        await self.session.commit()
        return context

    async def get_for_analysis_run(self, analysis_run_id: UUID) -> MarketSessionContext:
        context = await self.repository.get_by_analysis_run_id(analysis_run_id)
        if context is None:
            raise AppError(
                404, "market_session_context_not_found", "Market session context not found"
            )
        return context

    async def create_for_signal(self, signal_id: UUID) -> MarketSessionContext:
        signal = await self.session.get(Signal, signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        run = await self.session.get(AnalysisRun, signal.analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        context = await self.repository.create(
            MarketSessionContext(
                workspace_id=signal.workspace_id,
                analysis_run_id=signal.analysis_run_id,
                signal_id=signal.id,
                symbol_id=signal.symbol_id,
                timeframe=signal.timeframe,
                context_time=run.end_time,
                timezone_name=self.settings.market_session_default_timezone,
                session_version=self.settings.market_session_version,
                session_label=session_label(run.end_time).value,
                confidence_score=Decimal("1.0000"),
                context_json={"source": "signal_analysis_run", "hourUtc": run.end_time.hour},
            )
        )
        await self.session.commit()
        return context

    async def get_for_signal(self, signal_id: UUID) -> MarketSessionContext:
        context = await self.repository.get_by_signal_id(signal_id)
        if context is None:
            raise AppError(
                404, "market_session_context_not_found", "Market session context not found"
            )
        return context


def session_label(value: datetime) -> MarketSessionLabel:
    hour = value.hour
    if 7 <= hour < 12:
        return MarketSessionLabel.LONDON
    if 12 <= hour < 16:
        return MarketSessionLabel.OVERLAP
    if 16 <= hour < 21:
        return MarketSessionLabel.NEW_YORK
    if 0 <= hour < 7:
        return MarketSessionLabel.ASIA
    return MarketSessionLabel.OFF_HOURS
