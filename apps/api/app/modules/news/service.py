from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun, AnalysisRunStatus
from app.modules.analysis.repository import AnalysisRepository
from app.modules.features.repository import FeatureSnapshotRepository
from app.modules.news.models import (
    CorrelationLabel,
    DirectionAlignment,
    NewsEvent,
    NewsImportance,
    NewsSentiment,
    SignalNewsCorrelation,
    VolatilityReaction,
)
from app.modules.news.repository import NewsCorrelationRepository, NewsEventRepository
from app.modules.news.schemas import NewsEventCreate, NewsEventUpdate
from app.modules.signals.models import Signal, SignalBias, SignalRiskNote
from app.modules.signals.repository import SignalRepository
from app.modules.symbols.models import Symbol
from app.modules.symbols.repository import SymbolRepository

NEWS_CORRELATION_SCORER_VERSION = "news_correlation_v1"
NEWS_CORRELATION_WEIGHTS = {
    "timeProximity": Decimal("0.30"),
    "relevance": Decimal("0.25"),
    "importance": Decimal("0.20"),
    "magnitude": Decimal("0.15"),
    "sentiment": Decimal("0.10"),
}
IMPORTANCE_SCORES = {
    NewsImportance.CRITICAL.value: Decimal("1.00"),
    NewsImportance.HIGH.value: Decimal("0.80"),
    NewsImportance.MEDIUM.value: Decimal("0.50"),
    NewsImportance.LOW.value: Decimal("0.25"),
    NewsImportance.UNKNOWN.value: Decimal("0.30"),
}
EXACT_SYMBOL_RELEVANCE = Decimal("1.00")
ASSET_SYMBOL_RELEVANCE = Decimal("0.90")
BASE_ASSET_RELEVANCE = Decimal("0.75")
QUOTE_ASSET_RELEVANCE = Decimal("0.65")
USD_MACRO_RELEVANCE = Decimal("0.70")
GLOBAL_CRITICAL_RELEVANCE = Decimal("0.40")
UNKNOWN_SENTIMENT_SCORE = Decimal("0.50")
MISSING_FEATURE_MAGNITUDE_SCORE = Decimal("0.30")
CORRELATION_RISK_NOTE_CODE = "news_event_near_signal"


@dataclass(frozen=True)
class RelevanceResult:
    relevance_score: Decimal
    relevance_reason: str


@dataclass(frozen=True)
class ScoreResult:
    event: NewsEvent
    correlation_score: Decimal
    correlation_label: CorrelationLabel
    time_delta_minutes: Decimal
    direction_alignment: DirectionAlignment
    volatility_reaction: VolatilityReaction
    relevance_score: Decimal
    importance_score: Decimal
    magnitude_score: Decimal
    sentiment_score: Decimal
    reason: str
    metadata_json: dict[str, object]


class NewsEventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = NewsEventRepository(session)

    async def create_event(self, payload: NewsEventCreate) -> NewsEvent:
        event = NewsEvent(**payload.model_dump(mode="python"))
        try:
            created_event = await self.repository.create(event)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(409, "news_event_conflict", "News event could not be created") from error
        return created_event

    async def import_events(self, payloads: list[NewsEventCreate]) -> list[NewsEvent]:
        events: list[NewsEvent] = []
        try:
            for payload in payloads:
                event = NewsEvent(**payload.model_dump(mode="python"))
                events.append(await self.repository.create(event))
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "news_event_conflict",
                "News events could not be imported",
            ) from error
        return events

    async def list_events(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        currency: str | None = None,
        asset: str | None = None,
        symbol_id: UUID | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[NewsEvent]:
        return await self.repository.list_events(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            currency=currency.upper() if currency is not None else None,
            asset=asset.upper() if asset is not None else None,
            symbol_id=symbol_id,
            start_time=normalize_datetime(start_time),
            end_time=normalize_datetime(end_time),
        )

    async def get_event(self, news_event_id: UUID) -> NewsEvent:
        event = await self.repository.get_by_id(news_event_id)
        if event is None:
            raise AppError(404, "news_event_not_found", "News event not found")
        return event

    async def update_event(self, news_event_id: UUID, payload: NewsEventUpdate) -> NewsEvent:
        event = await self.get_event(news_event_id)
        updates = payload.model_dump(exclude_unset=True, mode="python")
        for field_name, field_value in updates.items():
            setattr(event, field_name, field_value)
        try:
            await self.session.flush()
            await self.session.refresh(event)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(409, "news_event_conflict", "News event could not be updated") from error
        return event


class NewsRelevanceService:
    def score_event_for_symbol(self, event: NewsEvent, symbol: Symbol) -> RelevanceResult:
        symbol_code = symbol.symbol.upper()
        base_asset = normalized_token(symbol.base_asset)
        quote_asset = normalized_token(symbol.quote_asset)
        event_asset = normalized_token(event.asset)
        event_currency = normalized_token(event.currency)

        if event.symbol_id == symbol.id:
            return RelevanceResult(EXACT_SYMBOL_RELEVANCE, "event_symbol_id_matched_signal_symbol")
        if event_asset == symbol_code:
            return RelevanceResult(ASSET_SYMBOL_RELEVANCE, "event_asset_matched_symbol")
        if event_asset is not None and event_asset == base_asset:
            return RelevanceResult(BASE_ASSET_RELEVANCE, "event_asset_matched_base_asset")
        if event_currency is not None and event_currency == base_asset:
            return RelevanceResult(BASE_ASSET_RELEVANCE, "event_currency_matched_base_asset")
        if event_asset is not None and event_asset == quote_asset:
            return RelevanceResult(QUOTE_ASSET_RELEVANCE, "event_asset_matched_quote_asset")
        if event_currency is not None and event_currency == quote_asset:
            if event_currency == "USD":
                return RelevanceResult(USD_MACRO_RELEVANCE, "usd_macro_event_matched_usd_pair")
            return RelevanceResult(QUOTE_ASSET_RELEVANCE, "event_currency_matched_quote_asset")
        if event_currency == "USD" and "USD" in {base_asset, quote_asset}:
            return RelevanceResult(USD_MACRO_RELEVANCE, "usd_macro_event_matched_usd_pair")
        if (
            event.importance == NewsImportance.CRITICAL.value
            and event.symbol_id is None
            and event_currency is None
            and event_asset is None
        ):
            return RelevanceResult(GLOBAL_CRITICAL_RELEVANCE, "critical_global_event")
        return RelevanceResult(Decimal("0.00"), "event_not_relevant_to_symbol")


class NewsCorrelationService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.event_repository = NewsEventRepository(session)
        self.correlation_repository = NewsCorrelationRepository(session)
        self.signal_repository = SignalRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.feature_repository = FeatureSnapshotRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.relevance_service = NewsRelevanceService()

    async def correlate_analysis_run_with_news(
        self,
        analysis_run_id: UUID,
        commit: bool = False,
    ) -> list[SignalNewsCorrelation]:
        run = await self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        signal = await self.signal_repository.get_by_analysis_run_id(run.id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return await self.correlate_signal(signal=signal, run=run, commit=commit)

    async def correlate_signal_with_news(
        self,
        signal_id: UUID,
        commit: bool = False,
    ) -> list[SignalNewsCorrelation]:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        run = await self.analysis_repository.get_run(signal.analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        return await self.correlate_signal(signal=signal, run=run, commit=commit)

    async def correlate_signal(
        self,
        signal: Signal,
        run: AnalysisRun,
        commit: bool = False,
    ) -> list[SignalNewsCorrelation]:
        if run.status not in {AnalysisRunStatus.COMPLETED, AnalysisRunStatus.RUNNING}:
            raise AppError(
                422,
                "analysis_run_not_correlatable",
                "Only completed or running analysis runs can be correlated with news",
            )
        await self.add_audit_log(
            run.id,
            "news_correlation_started",
            "Deterministic news correlation started",
            {"signalId": str(signal.id), "scorerVersion": NEWS_CORRELATION_SCORER_VERSION},
        )
        try:
            symbol = await self.symbol_repository.get_by_id(signal.symbol_id)
            if symbol is None:
                raise AppError(404, "symbol_not_found", "Symbol not found")
            feature_snapshot = await self.feature_repository.get_by_analysis_run_id(run.id)
            candidates = await self.load_candidate_events(run)
            scored_events = self.score_events(
                signal=signal,
                run=run,
                symbol=symbol,
                features=feature_snapshot.features_json if feature_snapshot is not None else None,
                events=candidates,
            )
            correlations = [
                self.build_correlation(signal=signal, score=score)
                for score in scored_events[: self.settings.news_correlation_max_events_per_signal]
            ]
            await self.correlation_repository.delete_for_signal(signal.id)
            persisted = await self.correlation_repository.create_many(correlations)
            await self.persist_risk_note_if_needed(signal, persisted)
            await self.add_audit_log(
                run.id,
                "news_correlation_completed",
                "Deterministic news correlation completed",
                {
                    "signalId": str(signal.id),
                    "correlationCount": len(persisted),
                    "scorerVersion": NEWS_CORRELATION_SCORER_VERSION,
                },
            )
            if commit:
                await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "news_correlation_conflict",
                "News correlations could not be persisted",
            ) from error
        except Exception:
            await self.add_audit_log(
                run.id,
                "news_correlation_failed",
                "Deterministic news correlation failed",
                {"signalId": str(signal.id)},
            )
            raise
        return persisted

    async def list_by_signal_id(self, signal_id: UUID) -> list[SignalNewsCorrelation]:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return await self.correlation_repository.list_by_signal_id(signal_id)

    async def list_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> list[SignalNewsCorrelation]:
        run = await self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        return await self.correlation_repository.list_by_analysis_run_id(analysis_run_id)

    async def load_candidate_events(self, run: AnalysisRun) -> list[NewsEvent]:
        start_time = run.start_time - timedelta(
            minutes=self.settings.news_correlation_post_event_minutes
        )
        end_time = run.end_time + timedelta(
            minutes=self.settings.news_correlation_pre_event_minutes
        )
        return await self.event_repository.find_candidates(
            workspace_id=run.workspace_id,
            start_time=start_time,
            end_time=end_time,
        )

    def score_events(
        self,
        signal: Signal,
        run: AnalysisRun,
        symbol: Symbol,
        features: Mapping[str, object] | None,
        events: list[NewsEvent],
    ) -> list[ScoreResult]:
        scores = [
            self.score_event(signal=signal, run=run, symbol=symbol, features=features, event=event)
            for event in events
        ]
        relevant_scores = [
            score
            for score in scores
            if score.relevance_score > 0 and score.correlation_label != CorrelationLabel.NONE
        ]
        return sorted(
            relevant_scores,
            key=lambda score: (score.correlation_score, score.relevance_score),
            reverse=True,
        )

    def score_event(
        self,
        signal: Signal,
        run: AnalysisRun,
        symbol: Symbol,
        features: Mapping[str, object] | None,
        event: NewsEvent,
    ) -> ScoreResult:
        relevance = self.relevance_service.score_event_for_symbol(event, symbol)
        time_score, time_delta_minutes = self.time_proximity_score(run, event)
        importance_score = IMPORTANCE_SCORES.get(event.importance, IMPORTANCE_SCORES["unknown"])
        magnitude_score, magnitude_metadata = self.magnitude_score(signal, features)
        sentiment_score, alignment, sentiment_metadata = self.sentiment_score(signal, event)
        weighted_score = (
            (time_score * NEWS_CORRELATION_WEIGHTS["timeProximity"])
            + (relevance.relevance_score * NEWS_CORRELATION_WEIGHTS["relevance"])
            + (importance_score * NEWS_CORRELATION_WEIGHTS["importance"])
            + (magnitude_score * NEWS_CORRELATION_WEIGHTS["magnitude"])
            + (sentiment_score * NEWS_CORRELATION_WEIGHTS["sentiment"])
        )
        correlation_score = quantize_score(weighted_score)
        label = correlation_label(correlation_score)
        volatility = volatility_reaction(signal.volatility_state)
        metadata: dict[str, object] = {
            "scorerVersion": NEWS_CORRELATION_SCORER_VERSION,
            "scorer_version": NEWS_CORRELATION_SCORER_VERSION,
            "weights": {key: str(value) for key, value in NEWS_CORRELATION_WEIGHTS.items()},
            "windowConfig": {
                "preEventMinutes": self.settings.news_correlation_pre_event_minutes,
                "postEventMinutes": self.settings.news_correlation_post_event_minutes,
            },
            "window_config": {
                "pre_event_minutes": self.settings.news_correlation_pre_event_minutes,
                "post_event_minutes": self.settings.news_correlation_post_event_minutes,
            },
            "timeScore": str(time_score),
            "relevanceReason": relevance.relevance_reason,
            "magnitude": magnitude_metadata,
            "sentiment": sentiment_metadata,
        }
        return ScoreResult(
            event=event,
            correlation_score=correlation_score,
            correlation_label=label,
            time_delta_minutes=time_delta_minutes,
            direction_alignment=alignment,
            volatility_reaction=volatility,
            relevance_score=quantize_score(relevance.relevance_score),
            importance_score=quantize_score(importance_score),
            magnitude_score=quantize_score(magnitude_score),
            sentiment_score=quantize_score(sentiment_score),
            reason=correlation_reason(label, event, time_delta_minutes, volatility),
            metadata_json=metadata,
        )

    def time_proximity_score(self, run: AnalysisRun, event: NewsEvent) -> tuple[Decimal, Decimal]:
        if run.start_time <= event.event_time <= run.end_time:
            return Decimal("1.00"), Decimal("0.0000")
        if event.event_time < run.start_time:
            delta = run.start_time - event.event_time
            minutes = decimal_minutes(delta)
        else:
            delta = event.event_time - run.end_time
            minutes = decimal_minutes(delta)
        absolute_minutes = abs(minutes)
        if absolute_minutes <= Decimal("5"):
            return Decimal("1.00"), minutes
        if absolute_minutes <= Decimal("15"):
            return Decimal("0.65"), minutes
        if absolute_minutes <= Decimal("30"):
            return Decimal("0.35"), minutes
        return Decimal("0.00"), minutes

    def magnitude_score(
        self,
        signal: Signal,
        features: Mapping[str, object] | None,
    ) -> tuple[Decimal, dict[str, object]]:
        if features is None:
            return MISSING_FEATURE_MAGNITUDE_SCORE, {"featureSnapshot": "missing"}
        pips_moved = abs_decimal(signal.pips_moved)
        ticks_moved = abs_decimal(signal.tick_moved)
        atr_expansion_ratio = decimal_feature(features, "volatility", "atrExpansionRatio")
        movement_quality = string_feature(features, "movement", "movementQuality") or (
            signal.movement_quality
        )
        volatility_state_value = signal.volatility_state or string_feature(
            features,
            "volatility",
            "volatilityState",
        )
        scores = [
            movement_size_score(pips_moved, ticks_moved),
            atr_score(atr_expansion_ratio),
            volatility_score(volatility_state_value),
            movement_quality_score(movement_quality),
        ]
        resolved_score = max(scores)
        return resolved_score, {
            "featureSnapshot": "present",
            "pipsMoved": str(pips_moved) if pips_moved is not None else None,
            "ticksMoved": str(ticks_moved) if ticks_moved is not None else None,
            "atrExpansionRatio": (
                str(atr_expansion_ratio) if atr_expansion_ratio is not None else None
            ),
            "volatilityState": volatility_state_value,
            "movementQuality": movement_quality,
        }

    def sentiment_score(
        self,
        signal: Signal,
        event: NewsEvent,
    ) -> tuple[Decimal, DirectionAlignment, dict[str, object]]:
        if event.sentiment == NewsSentiment.UNKNOWN.value:
            return (
                UNKNOWN_SENTIMENT_SCORE,
                DirectionAlignment.UNKNOWN,
                {"sentimentKnown": False, "handling": "neutral_score"},
            )
        if event.sentiment in {NewsSentiment.NEUTRAL.value, NewsSentiment.MIXED.value}:
            return (
                Decimal("0.50"),
                DirectionAlignment.NEUTRAL,
                {"sentimentKnown": True, "handling": "neutral_or_mixed"},
            )
        if signal.bias not in {SignalBias.BULLISH.value, SignalBias.BEARISH.value}:
            return (
                Decimal("0.50"),
                DirectionAlignment.NEUTRAL,
                {"sentimentKnown": True, "handling": "non_directional_signal"},
            )
        if event.sentiment == signal.bias:
            return Decimal("1.00"), DirectionAlignment.ALIGNED, {"sentimentKnown": True}
        return Decimal("0.20"), DirectionAlignment.OPPOSED, {"sentimentKnown": True}

    def build_correlation(self, signal: Signal, score: ScoreResult) -> SignalNewsCorrelation:
        return SignalNewsCorrelation(
            workspace_id=signal.workspace_id,
            analysis_run_id=signal.analysis_run_id,
            signal_id=signal.id,
            news_event_id=score.event.id,
            correlation_score=score.correlation_score,
            correlation_label=score.correlation_label.value,
            time_delta_minutes=score.time_delta_minutes,
            direction_alignment=score.direction_alignment.value,
            volatility_reaction=score.volatility_reaction.value,
            relevance_score=score.relevance_score,
            importance_score=score.importance_score,
            magnitude_score=score.magnitude_score,
            sentiment_score=score.sentiment_score,
            reason=score.reason,
            metadata_json=score.metadata_json,
        )

    async def persist_risk_note_if_needed(
        self,
        signal: Signal,
        correlations: list[SignalNewsCorrelation],
    ) -> None:
        if not any(
            correlation.correlation_label == CorrelationLabel.STRONG.value
            for correlation in correlations
        ):
            return
        existing_notes = await self.signal_repository.list_risk_notes(signal.id)
        if any(note.code == CORRELATION_RISK_NOTE_CODE for note in existing_notes):
            return
        self.session.add(
            SignalRiskNote(
                signal_id=signal.id,
                code=CORRELATION_RISK_NOTE_CODE,
                message=(
                    "A relevant market event occurred near this signal window. "
                    "Volatility may be event-driven."
                ),
                severity="medium",
                metadata_json={"scorerVersion": NEWS_CORRELATION_SCORER_VERSION},
            )
        )
        await self.session.flush()

    async def add_audit_log(
        self,
        analysis_run_id: UUID,
        event_type: str,
        message: str,
        metadata_json: dict[str, object] | None = None,
    ) -> AnalysisAuditLog:
        return await self.analysis_repository.add_audit_log(
            AnalysisAuditLog(
                analysis_run_id=analysis_run_id,
                event_type=event_type,
                message=message,
                metadata_json=metadata_json,
            )
        )


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalized_token(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def decimal_minutes(delta: timedelta) -> Decimal:
    return Decimal(str(delta.total_seconds() / 60)).quantize(Decimal("0.0001"))


def quantize_score(value: Decimal) -> Decimal:
    return max(Decimal("0.0000"), min(Decimal("1.0000"), value)).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )


def correlation_label(score: Decimal) -> CorrelationLabel:
    if score < Decimal("0.2500"):
        return CorrelationLabel.NONE
    if score < Decimal("0.5000"):
        return CorrelationLabel.WEAK
    if score < Decimal("0.7500"):
        return CorrelationLabel.POSSIBLE
    return CorrelationLabel.STRONG


def abs_decimal(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return abs(value)


def decimal_feature(
    features: Mapping[str, object] | None,
    section_name: str,
    field_name: str,
) -> Decimal | None:
    if features is None:
        return None
    section = features.get(section_name)
    if not isinstance(section, Mapping):
        return None
    value = section.get(field_name)
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def string_feature(
    features: Mapping[str, object] | None,
    section_name: str,
    field_name: str,
) -> str | None:
    if features is None:
        return None
    section = features.get(section_name)
    if not isinstance(section, Mapping):
        return None
    value = section.get(field_name)
    return value if isinstance(value, str) else None


def movement_size_score(pips_moved: Decimal | None, ticks_moved: Decimal | None) -> Decimal:
    if pips_moved is not None:
        if pips_moved >= Decimal("20"):
            return Decimal("1.00")
        if pips_moved >= Decimal("10"):
            return Decimal("0.75")
        if pips_moved >= Decimal("5"):
            return Decimal("0.50")
        if pips_moved > Decimal("0"):
            return Decimal("0.25")
    if ticks_moved is not None:
        if ticks_moved >= Decimal("200"):
            return Decimal("1.00")
        if ticks_moved >= Decimal("100"):
            return Decimal("0.75")
        if ticks_moved >= Decimal("50"):
            return Decimal("0.50")
        if ticks_moved > Decimal("0"):
            return Decimal("0.25")
    return Decimal("0.20")


def atr_score(atr_expansion_ratio: Decimal | None) -> Decimal:
    if atr_expansion_ratio is None:
        return Decimal("0.20")
    if atr_expansion_ratio >= Decimal("2.00"):
        return Decimal("1.00")
    if atr_expansion_ratio >= Decimal("1.25"):
        return Decimal("0.75")
    if atr_expansion_ratio > Decimal("0"):
        return Decimal("0.35")
    return Decimal("0.20")


def volatility_score(value: str | None) -> Decimal:
    if value == "spike":
        return Decimal("1.00")
    if value in {"elevated", "expanding"}:
        return Decimal("0.75")
    if value == "normal":
        return Decimal("0.40")
    if value == "compressed":
        return Decimal("0.25")
    return Decimal("0.20")


def movement_quality_score(value: str | None) -> Decimal:
    if value == "efficient":
        return Decimal("0.80")
    if value == "mixed":
        return Decimal("0.50")
    if value == "choppy":
        return Decimal("0.25")
    return Decimal("0.20")


def volatility_reaction(value: str | None) -> VolatilityReaction:
    if value == "spike":
        return VolatilityReaction.SPIKE
    if value in {"elevated", "expanding"}:
        return VolatilityReaction.ELEVATED
    if value == "normal":
        return VolatilityReaction.NORMAL
    if value == "compressed":
        return VolatilityReaction.NONE
    return VolatilityReaction.UNKNOWN


def correlation_reason(
    label: CorrelationLabel,
    event: NewsEvent,
    time_delta_minutes: Decimal,
    volatility: VolatilityReaction,
) -> str:
    importance = event.importance.replace("_", " ")
    distance = abs(time_delta_minutes)
    timing = f"{distance.normalize()} minutes from the signal window"
    if label == CorrelationLabel.STRONG:
        return (
            f"Strong possible correlation detected because a {importance}-importance event "
            f"happened {timing} and volatility was {volatility.value}."
        )
    if label == CorrelationLabel.POSSIBLE:
        return (
            f"Possible correlation detected because a {importance}-importance event happened "
            f"{timing} and may have contributed to volatility."
        )
    if label == CorrelationLabel.WEAK:
        return f"Weak correlation detected because the event was relevant but happened {timing}."
    return "No strong event correlation was found inside the configured event window."
