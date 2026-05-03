from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.repository import AnalysisRepository
from app.modules.explanations.repository import DeterministicExplanationRepository
from app.modules.features.repository import FeatureSnapshotRepository
from app.modules.historical_cases.models import HistoricalCaseSearch, HistoricalCaseVector
from app.modules.historical_cases.repository import HistoricalCaseRepository
from app.modules.historical_cases.schemas import (
    HistoricalCaseBackfillRead,
    HistoricalCaseContextRead,
    HistoricalCaseSearchFilters,
    HistoricalCaseSearchRead,
    HistoricalCaseSearchResult,
    HistoricalCaseSignalSummary,
    HistoricalCaseVectorRead,
)
from app.modules.historical_cases.similarity import build_case_vector, score_similarity
from app.modules.indicators.repository import IndicatorSnapshotRepository
from app.modules.news.repository import NewsCorrelationRepository
from app.modules.outcomes.repository import OutcomeRepository
from app.modules.signals.models import Signal
from app.modules.signals.repository import SignalRepository
from app.modules.symbols.repository import SymbolRepository


class HistoricalCaseService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = HistoricalCaseRepository(session)
        self.signal_repository = SignalRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.feature_repository = FeatureSnapshotRepository(session)
        self.indicator_repository = IndicatorSnapshotRepository(session)
        self.news_repository = NewsCorrelationRepository(session)
        self.outcome_repository = OutcomeRepository(session)
        self.explanation_repository = DeterministicExplanationRepository(session)

    async def build_case_vector_for_signal(
        self,
        signal_id: UUID,
        force_recompute: bool = False,
    ) -> HistoricalCaseVectorRead:
        signal = await self.get_signal(signal_id)
        existing = await self.repository.get_vector_by_signal_id(
            signal_id,
            self.settings.historical_case_vector_version,
        )
        if existing is not None and not force_recompute:
            return HistoricalCaseVectorRead.model_validate(existing)
        symbol = await self.symbol_repository.get_by_id(signal.symbol_id)
        features = await self.feature_repository.get_by_analysis_run_id(signal.analysis_run_id)
        indicators = await self.indicator_repository.get_by_analysis_run_id(signal.analysis_run_id)
        outcomes = await self.outcome_repository.list_by_signal_id(signal.id)
        news_correlations = await self.news_repository.list_by_signal_id(signal.id)
        explanation = await self.explanation_repository.get_by_signal_id(signal.id)
        feature_summary = summarize_features(signal, features.features_json if features is not None else None)
        indicator_summary = summarize_indicators(indicators.indicators_json if indicators is not None else None)
        outcome_summary = summarize_outcomes(outcomes)
        news_summary = summarize_news(news_correlations)
        signal_summary = summarize_signal(signal)
        symbol_summary = {
            "symbolId": str(signal.symbol_id),
            "symbol": symbol.symbol if symbol is not None else None,
            "marketType": symbol.market_type if symbol is not None else None,
        }
        vector_json = build_case_vector(
            signal_summary=signal_summary,
            feature_summary=feature_summary,
            indicator_summary=indicator_summary,
            outcome_summary=outcome_summary,
            news_summary=news_summary,
            symbol_summary=symbol_summary,
            vector_version=self.settings.historical_case_vector_version,
        )
        vector = HistoricalCaseVector(
            workspace_id=signal.workspace_id,
            analysis_run_id=signal.analysis_run_id,
            signal_id=signal.id,
            symbol_id=signal.symbol_id,
            timeframe=signal.timeframe,
            strategy_profile_key=signal.strategy_profile_key,
            strategy_profile_version=signal.strategy_profile_version,
            pattern_type=signal.pattern_type,
            bias=signal.bias,
            classification_status=signal.classification_status,
            confidence_score=signal.confidence_score,
            vector_version=self.settings.historical_case_vector_version,
            vector_json=vector_json,
            feature_summary_json=feature_summary,
            indicator_summary_json=indicator_summary,
            outcome_summary_json=outcome_summary,
            metadata_json={
                "symbol": symbol_summary,
                "signalSummary": signal.summary,
                "deterministicExplanationSummary": (
                    explanation.short_summary if explanation is not None else None
                ),
                "source": "persisted_deterministic_artifacts",
            },
        )
        persisted = await self.repository.upsert_vector(vector, force_recompute=force_recompute)
        await self.session.commit()
        return HistoricalCaseVectorRead.model_validate(persisted)

    async def get_case_vector(self, signal_id: UUID) -> HistoricalCaseVectorRead:
        vector = await self.repository.get_vector_by_signal_id(
            signal_id,
            self.settings.historical_case_vector_version,
        )
        if vector is None:
            raise AppError(404, "historical_case_vector_not_found", "Historical case vector not found")
        return HistoricalCaseVectorRead.model_validate(vector)

    async def search_similar_cases_for_signal(
        self,
        signal_id: UUID,
        filters: HistoricalCaseSearchFilters,
        limit: int | None,
    ) -> HistoricalCaseSearchRead:
        source_vector = await self.ensure_vector(signal_id)
        return await self.search_from_vector(
            source_vector=source_vector,
            filters=filters,
            limit=limit,
            source_analysis_run_id=source_vector.analysis_run_id,
        )

    async def search_similar_cases_for_analysis_run(
        self,
        analysis_run_id: UUID,
        filters: HistoricalCaseSearchFilters,
        limit: int | None,
    ) -> HistoricalCaseSearchRead:
        signal = await self.signal_repository.get_by_analysis_run_id(analysis_run_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found for analysis run")
        return await self.search_similar_cases_for_signal(signal.id, filters, limit)

    async def backfill_case_vectors(
        self,
        workspace_id: UUID,
        limit: int,
        force_recompute: bool = False,
    ) -> HistoricalCaseBackfillRead:
        resolved_limit = self.clamp_limit(limit)
        signals = await self.repository.list_backfill_signals(
            workspace_id=workspace_id,
            vector_version=self.settings.historical_case_vector_version,
            limit=resolved_limit,
            force_recompute=force_recompute,
        )
        built_count = 0
        skipped_count = 0
        for signal in signals:
            existing = await self.repository.get_vector_by_signal_id(
                signal.id,
                self.settings.historical_case_vector_version,
            )
            if existing is not None and not force_recompute:
                skipped_count += 1
                continue
            await self.build_case_vector_for_signal(signal.id, force_recompute=force_recompute)
            built_count += 1
        return HistoricalCaseBackfillRead(
            workspace_id=workspace_id,
            vector_version=self.settings.historical_case_vector_version,
            requested_limit=resolved_limit,
            built_count=built_count,
            skipped_count=skipped_count,
            force_recompute=force_recompute,
        )

    async def get_historical_context_for_signal(
        self,
        signal_id: UUID,
        filters: HistoricalCaseSearchFilters,
        limit: int | None = None,
    ) -> HistoricalCaseContextRead:
        search = await self.search_similar_cases_for_signal(signal_id, filters, limit)
        return HistoricalCaseContextRead(
            source_signal_id=signal_id,
            search_version=search.search_version,
            cases=search.results,
        )

    async def ensure_vector(self, signal_id: UUID) -> HistoricalCaseVector:
        vector = await self.repository.get_vector_by_signal_id(
            signal_id,
            self.settings.historical_case_vector_version,
        )
        if vector is not None:
            return vector
        await self.build_case_vector_for_signal(signal_id)
        built = await self.repository.get_vector_by_signal_id(
            signal_id,
            self.settings.historical_case_vector_version,
        )
        if built is None:
            raise AppError(500, "historical_case_vector_build_failed", "Historical case vector build failed")
        return built

    async def search_from_vector(
        self,
        source_vector: HistoricalCaseVector,
        filters: HistoricalCaseSearchFilters,
        limit: int | None,
        source_analysis_run_id: UUID | None,
    ) -> HistoricalCaseSearchRead:
        if filters.workspace_id != source_vector.workspace_id:
            raise AppError(422, "workspace_mismatch", "Search workspace must match the source case workspace")
        resolved_limit = self.clamp_limit(limit or self.settings.historical_case_default_limit)
        candidate_limit = max(resolved_limit * 5, resolved_limit)
        candidates = await self.repository.list_candidate_vectors(
            workspace_id=filters.workspace_id,
            vector_version=self.settings.historical_case_vector_version,
            limit=candidate_limit,
            symbol_id=filters.symbol_id,
            timeframe=filters.timeframe,
            strategy_profile_key=filters.strategy_profile_key,
            pattern_type=filters.pattern_type,
            bias=filters.bias,
            classification_status=filters.classification_status,
            exclude_signal_id=source_vector.signal_id if filters.exclude_same_signal else None,
        )
        min_score = (
            filters.min_score
            if filters.min_score is not None
            else self.settings.historical_case_min_score
        )
        results = []
        for candidate in candidates:
            scored = score_similarity(
                source_vector=source_vector.vector_json,
                candidate_vector=candidate.vector_json,
                include_outcomes=filters.include_outcomes,
            )
            if scored.score < min_score:
                continue
            results.append(self.build_search_result(candidate, scored))
        results = sorted(results, key=lambda item: item.similarity_score, reverse=True)[:resolved_limit]
        search = HistoricalCaseSearch(
            workspace_id=filters.workspace_id,
            source_signal_id=source_vector.signal_id,
            source_analysis_run_id=source_analysis_run_id,
            search_version=self.settings.historical_case_vector_version,
            filters_json=filters.model_dump(mode="json", by_alias=True),
            result_count=len(results),
            results_json=[result.model_dump(mode="json", by_alias=True) for result in results],
        )
        await self.repository.create_search(search)
        await self.session.commit()
        return HistoricalCaseSearchRead(
            source_signal_id=source_vector.signal_id,
            source_analysis_run_id=source_analysis_run_id,
            search_version=self.settings.historical_case_vector_version,
            result_count=len(results),
            results=results,
        )

    def build_search_result(self, candidate: HistoricalCaseVector, scored: Any) -> HistoricalCaseSearchResult:
        signal_section = section(candidate.vector_json, "signal")
        metadata = candidate.metadata_json
        return HistoricalCaseSearchResult(
            matched_signal_id=candidate.signal_id,
            analysis_run_id=candidate.analysis_run_id,
            similarity_score=scored.score,
            matched_reasons=scored.matched_reasons,
            differing_reasons=scored.differing_reasons,
            signal_summary=HistoricalCaseSignalSummary(
                signal_id=candidate.signal_id,
                symbol_id=candidate.symbol_id,
                timeframe=candidate.timeframe,
                strategy_profile_key=candidate.strategy_profile_key,
                strategy_profile_version=candidate.strategy_profile_version,
                pattern_type=candidate.pattern_type,
                bias=candidate.bias,
                classification_status=candidate.classification_status,
                confidence_score=candidate.confidence_score,
                confidence_label=string_or_none(signal_section.get("confidenceLabel")),
                summary=string_or_none(metadata.get("signalSummary")),
            ),
            outcome_summary=candidate.outcome_summary_json,
            deterministic_explanation_summary=string_or_none(metadata.get("deterministicExplanationSummary")),
        )

    async def get_signal(self, signal_id: UUID) -> Signal:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return signal

    def clamp_limit(self, limit: int) -> int:
        return min(max(limit, 1), self.settings.historical_case_max_limit)


def summarize_signal(signal: Signal) -> dict[str, object]:
    return {
        "bias": signal.bias,
        "classificationStatus": signal.classification_status,
        "patternType": signal.pattern_type,
        "strategyProfileKey": signal.strategy_profile_key,
        "strategyProfileVersion": signal.strategy_profile_version,
        "confidenceScore": str(signal.confidence_score) if signal.confidence_score is not None else None,
        "confidenceLabel": signal.confidence_label,
        "timeframe": signal.timeframe,
        "summary": signal.summary,
    }


def summarize_features(signal: Signal, features: dict[str, object] | None) -> dict[str, object]:
    movement = section(features, "movement")
    volatility = section(features, "volatility")
    trend = section(features, "trend")
    range_section = section(features, "range")
    return {
        "movementDirection": signal.movement_direction or string_or_none(movement.get("netDirection")),
        "volatilityState": signal.volatility_state or string_or_none(volatility.get("volatilityState")),
        "trendState": signal.trend_state or string_or_none(trend.get("trendState")),
        "rangeState": signal.range_state or string_or_none(range_section.get("rangeState")),
        "movementQuality": signal.movement_quality,
        "pipsMoved": (
            str(signal.pips_moved)
            if signal.pips_moved is not None
            else string_or_none(movement.get("pipsMoved"))
        ),
        "ticksMoved": (
            str(signal.tick_moved)
            if signal.tick_moved is not None
            else string_or_none(movement.get("ticksMoved"))
        ),
    }


def summarize_indicators(indicators: dict[str, object] | None) -> dict[str, object]:
    ema = section(indicators, "ema")
    rsi = section(indicators, "rsi")
    macd = section(indicators, "macd")
    atr = section(indicators, "atr")
    return {
        "emaAlignment": first_present(ema, ("alignment", "emaAlignment", "state")),
        "rsiState": first_present(rsi, ("state", "rsiState", "zone")),
        "macdState": first_present(macd, ("state", "macdState", "signal")),
        "atrState": first_present(atr, ("state", "atrState", "volatilityState")),
    }


def summarize_outcomes(outcomes: list[Any]) -> dict[str, object] | None:
    if not outcomes:
        return None
    labels = [str(outcome.outcome_label) for outcome in outcomes]
    return {
        "outcomeLabels": sorted(set(labels)),
        "horizons": sorted({int(outcome.horizon_minutes) for outcome in outcomes}),
        "evaluatedCount": len(outcomes),
        "labelsByHorizon": [
            {
                "horizonMinutes": outcome.horizon_minutes,
                "outcomeLabel": outcome.outcome_label,
                "evaluationStatus": outcome.evaluation_status,
                "directionFollowed": outcome.direction_followed,
                "reversalDetected": outcome.reversal_detected,
                "movementQuality": outcome.movement_quality,
            }
            for outcome in outcomes
        ],
    }


def summarize_news(correlations: list[Any]) -> dict[str, object]:
    if not correlations:
        return {"correlationLabel": None, "directionAlignment": None, "volatilityReaction": None}
    ordered = sorted(correlations, key=lambda item: item.correlation_score, reverse=True)
    strongest = ordered[0]
    return {
        "correlationLabel": strongest.correlation_label,
        "directionAlignment": strongest.direction_alignment,
        "volatilityReaction": strongest.volatility_reaction,
    }


def section(payload: dict[str, object] | None, key: str) -> dict[str, object]:
    if payload is None:
        return {}
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def first_present(payload: dict[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = string_or_none(payload.get(key))
        if value is not None:
            return value
    return None


def string_or_none(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
