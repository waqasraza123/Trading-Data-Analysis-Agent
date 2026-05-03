from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.event_studies.calculator import (
    EventStudyCalculation,
    EventStudyCalculationRequest,
    EventStudyCalculator,
)
from app.modules.event_studies.models import (
    EventStudyReactionLabel,
    EventStudyResult,
    EventStudyRun,
    EventStudyRunStatus,
)
from app.modules.event_studies.repository import EventStudyRepository
from app.modules.event_studies.schemas import EventStudyRunRequest
from app.modules.news.repository import NewsEventRepository
from app.modules.symbols.models import Symbol

SUMMARY_TOP_OBSERVED_MOVES_LIMIT = 10


class EventStudyService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = EventStudyRepository(session)
        self.news_repository = NewsEventRepository(session)
        self.calculator = EventStudyCalculator()

    async def run_event_study(self, payload: EventStudyRunRequest) -> EventStudyRun:
        event = await self.news_repository.get_by_id(payload.news_event_id)
        if event is None:
            raise AppError(404, "news_event_not_found", "News event not found")
        if event.workspace_id is not None and event.workspace_id != payload.workspace_id:
            raise AppError(
                422,
                "news_event_workspace_mismatch",
                "News event does not belong to the requested workspace",
            )
        pre_event_minutes = (
            payload.pre_event_minutes
            if payload.pre_event_minutes is not None
            else self.settings.event_study_default_pre_event_minutes
        )
        post_event_minutes = (
            payload.post_event_minutes
            if payload.post_event_minutes is not None
            else self.settings.event_study_default_post_event_minutes
        )
        run = EventStudyRun(
            workspace_id=payload.workspace_id,
            news_event_id=payload.news_event_id,
            status=EventStudyRunStatus.PENDING.value,
            event_study_version=self.settings.event_study_version,
            pre_event_minutes=pre_event_minutes,
            post_event_minutes=post_event_minutes,
            symbol_filters_json={
                "symbolIds": [str(symbol_id) for symbol_id in payload.symbol_ids],
                "timeframes": payload.timeframes,
            },
            analyzed_symbol_count=0,
            result_count=0,
            summary={},
        )
        try:
            run = await self.repository.create_run(run)
            symbols = await self.load_symbols(event_symbol_id=event.symbol_id, payload=payload)
            event_time = normalize_datetime(event.event_time)
            window_start = event_time - timedelta(minutes=pre_event_minutes)
            window_end = event_time + timedelta(minutes=post_event_minutes)
            results = await self.calculate_results(
                run=run,
                symbols=symbols,
                timeframes=payload.timeframes,
                event_time=event_time,
                window_start=window_start,
                window_end=window_end,
            )
            persisted_results = await self.repository.create_results(results) if results else []
            run.analyzed_symbol_count = len(symbols)
            run.result_count = len(persisted_results)
            run.summary = build_summary(symbols=symbols, results=persisted_results)
            run.status = run_status_for_results(symbols=symbols, results=persisted_results)
            await self.session.commit()
            await self.session.refresh(run)
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "event_study_conflict",
                "Event study could not be persisted",
            ) from error
        except AppError:
            await self.session.rollback()
            raise
        except Exception as error:
            await self.session.rollback()
            failed_run = await self.repository.get_run(run.id)
            if failed_run is not None:
                failed_run.status = EventStudyRunStatus.FAILED.value
                failed_run.error_message = "Event study failed during deterministic calculation"
                await self.session.commit()
            raise AppError(500, "event_study_failed", "Event study calculation failed") from error
        return run

    async def load_symbols(
        self,
        event_symbol_id: UUID | None,
        payload: EventStudyRunRequest,
    ) -> list[Symbol]:
        if payload.symbol_ids:
            symbols = await self.repository.list_symbols_by_ids(payload.symbol_ids)
            missing_count = len(set(payload.symbol_ids)) - len(symbols)
            if missing_count > 0:
                raise AppError(404, "symbol_not_found", "One or more symbols were not found")
            return symbols
        event = await self.news_repository.get_by_id(payload.news_event_id)
        if event is None:
            raise AppError(404, "news_event_not_found", "News event not found")
        symbols = await self.repository.list_relevant_symbols(event)
        if event_symbol_id is not None and not symbols:
            raise AppError(404, "symbol_not_found", "News event symbol was not found")
        return symbols

    async def calculate_results(
        self,
        run: EventStudyRun,
        symbols: list[Symbol],
        timeframes: list[str],
        event_time: datetime,
        window_start: datetime,
        window_end: datetime,
    ) -> list[EventStudyResult]:
        results: list[EventStudyResult] = []
        for symbol in symbols:
            for timeframe in timeframes:
                source_ids = await self.repository.list_source_ids_for_window(
                    workspace_id=run.workspace_id,
                    symbol_id=symbol.id,
                    timeframe=timeframe,
                    start_time=window_start,
                    end_time=window_end,
                )
                if not source_ids:
                    results.append(
                        self.build_result(
                            run=run,
                            symbol=symbol,
                            source_id=None,
                            calculation=await self.calculate_for_source(
                                run=run,
                                symbol=symbol,
                                timeframe=timeframe,
                                event_time=event_time,
                                source_id=None,
                            ),
                        )
                    )
                    continue
                for source_id in source_ids:
                    calculation = await self.calculate_for_source(
                        run=run,
                        symbol=symbol,
                        timeframe=timeframe,
                        event_time=event_time,
                        source_id=source_id,
                    )
                    results.append(
                        self.build_result(
                            run=run,
                            symbol=symbol,
                            source_id=source_id,
                            calculation=calculation,
                        )
                    )
        return results

    async def calculate_for_source(
        self,
        run: EventStudyRun,
        symbol: Symbol,
        timeframe: str,
        event_time: datetime,
        source_id: UUID | None,
    ) -> EventStudyCalculation:
        pre_window_start = event_time - timedelta(minutes=run.pre_event_minutes)
        post_window_end = event_time + timedelta(minutes=run.post_event_minutes)
        pre_candles = await self.repository.list_final_candles(
            workspace_id=run.workspace_id,
            symbol_id=symbol.id,
            timeframe=timeframe,
            start_time=pre_window_start,
            end_time=event_time,
            source_id=source_id,
            include_end=False,
        )
        post_candles = await self.repository.list_final_candles(
            workspace_id=run.workspace_id,
            symbol_id=symbol.id,
            timeframe=timeframe,
            start_time=event_time,
            end_time=post_window_end,
            source_id=source_id,
            include_end=True,
        )
        return self.calculator.calculate(
            EventStudyCalculationRequest(
                symbol=symbol,
                timeframe=timeframe,
                event_time=event_time,
                pre_event_minutes=run.pre_event_minutes,
                post_event_minutes=run.post_event_minutes,
                minimum_candles=self.settings.event_study_min_candles,
                strong_reaction_multiplier=self.settings.event_study_strong_reaction_multiplier,
                moderate_reaction_multiplier=self.settings.event_study_moderate_reaction_multiplier,
                pre_candles=pre_candles,
                post_candles=post_candles,
            )
        )

    def build_result(
        self,
        run: EventStudyRun,
        symbol: Symbol,
        source_id: UUID | None,
        calculation: EventStudyCalculation,
    ) -> EventStudyResult:
        return EventStudyResult(
            workspace_id=run.workspace_id,
            event_study_run_id=run.id,
            news_event_id=run.news_event_id,
            symbol_id=symbol.id,
            source_id=source_id,
            timeframe=calculation.timeframe,
            event_time=calculation.event_time,
            pre_window_start=calculation.pre_window_start,
            pre_window_end=calculation.pre_window_end,
            post_window_start=calculation.post_window_start,
            post_window_end=calculation.post_window_end,
            pre_candle_count=calculation.pre_candle_count,
            post_candle_count=calculation.post_candle_count,
            pre_move=calculation.pre_move,
            post_move=calculation.post_move,
            post_move_pips=calculation.post_move_pips,
            post_move_ticks=calculation.post_move_ticks,
            pre_volatility_json=calculation.pre_volatility_json,
            post_volatility_json=calculation.post_volatility_json,
            volatility_reaction=calculation.volatility_reaction.value,
            direction_label=calculation.direction_label.value,
            reaction_label=calculation.reaction_label.value,
            data_quality_label=calculation.data_quality_label.value,
            metadata_json=calculation.metadata_json,
        )

    async def get_run(self, run_id: UUID) -> EventStudyRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "event_study_run_not_found", "Event study run not found")
        return run

    async def list_results(
        self,
        run_id: UUID,
        limit: int,
        offset: int,
    ) -> list[EventStudyResult]:
        await self.get_run(run_id)
        return await self.repository.list_results(run_id=run_id, limit=limit, offset=offset)

    async def list_runs_by_news_event(
        self,
        news_event_id: UUID,
        limit: int,
        offset: int,
    ) -> list[EventStudyRun]:
        event = await self.news_repository.get_by_id(news_event_id)
        if event is None:
            raise AppError(404, "news_event_not_found", "News event not found")
        return await self.repository.list_runs_by_news_event(
            news_event_id=news_event_id,
            limit=limit,
            offset=offset,
        )


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def run_status_for_results(
    symbols: list[Symbol],
    results: list[EventStudyResult],
) -> str:
    if not symbols or not results:
        return EventStudyRunStatus.COMPLETED_WITH_WARNINGS.value
    if any(result.reaction_label == EventStudyReactionLabel.INSUFFICIENT_DATA.value for result in results):
        return EventStudyRunStatus.COMPLETED_WITH_WARNINGS.value
    return EventStudyRunStatus.COMPLETED.value


def build_summary(symbols: list[Symbol], results: list[EventStudyResult]) -> dict[str, object]:
    reaction_counts = Counter(result.reaction_label for result in results)
    volatility_counts = Counter(result.volatility_reaction for result in results)
    direction_counts = Counter(result.direction_label for result in results)
    sorted_results = sorted(
        results,
        key=lambda result: abs(result.post_move),
        reverse=True,
    )
    return {
        "analyzedSymbolCount": len(symbols),
        "resultCount": len(results),
        "reactionCounts": dict(reaction_counts),
        "volatilityReactionCounts": dict(volatility_counts),
        "directionCounts": dict(direction_counts),
        "strongestObservedMoves": [
            {
                "symbolId": str(result.symbol_id),
                "sourceId": str(result.source_id) if result.source_id is not None else None,
                "timeframe": result.timeframe,
                "postMove": str(result.post_move),
                "postMovePips": str(result.post_move_pips) if result.post_move_pips is not None else None,
                "postMoveTicks": str(result.post_move_ticks)
                if result.post_move_ticks is not None
                else None,
                "reactionLabel": result.reaction_label,
                "volatilityReaction": result.volatility_reaction,
            }
            for result in sorted_results[:SUMMARY_TOP_OBSERVED_MOVES_LIMIT]
        ],
        "languagePolicy": {
            "usesEventWindowLanguage": True,
            "doesNotClaimCausation": True,
            "doesNotProvideFinancialAdvice": True,
            "doesNotCreateAlerts": True,
        },
    }
