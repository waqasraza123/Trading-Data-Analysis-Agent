from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.analysis.models import AnalysisMode, AnalysisRun, AnalysisRunStatus
from app.modules.news.models import CorrelationLabel, DirectionAlignment, NewsEvent, NewsEventType
from app.modules.news.schemas import NewsEventCreate
from app.modules.news.service import (
    IMPORTANCE_SCORES,
    NewsCorrelationService,
    NewsRelevanceService,
    correlation_label,
)
from app.modules.signals.models import (
    Signal,
    SignalBias,
    SignalClassificationStatus,
    SignalConfidenceLabel,
)
from app.modules.symbols.models import MarketType, Symbol


def test_news_event_validation_normalizes_required_fields() -> None:
    payload = NewsEventCreate(
        source=" manual ",
        title=" USD CPI Release ",
        eventTime="2026-04-29T12:30:00+05:00",
        currency=" usd ",
        asset=" eurusd ",
        importance="high",
    )

    assert payload.source == "manual"
    assert payload.title == "USD CPI Release"
    assert payload.currency == "USD"
    assert payload.asset == "EURUSD"
    assert payload.event_time == datetime(2026, 4, 29, 7, 30, tzinfo=UTC)
    assert payload.event_type == NewsEventType.MANUAL
    assert payload.sentiment == "unknown"
    assert payload.raw_payload_json["currency"] == " usd "


def test_news_event_validation_treats_naive_datetime_as_utc() -> None:
    payload = NewsEventCreate(
        source="manual",
        title="Manual market event",
        event_time=datetime(2026, 4, 29, 12, 30),
    )

    assert payload.event_time == datetime(2026, 4, 29, 12, 30, tzinfo=UTC)


def test_relevance_exact_symbol_match() -> None:
    symbol = symbol_fixture()
    event = event_fixture(symbol_id=symbol.id)

    result = NewsRelevanceService().score_event_for_symbol(event, symbol)

    assert result.relevance_score == Decimal("1.00")
    assert result.relevance_reason == "event_symbol_id_matched_signal_symbol"


def test_relevance_base_asset_match() -> None:
    symbol = symbol_fixture()
    event = event_fixture(currency="EUR")

    result = NewsRelevanceService().score_event_for_symbol(event, symbol)

    assert result.relevance_score == Decimal("0.75")


def test_relevance_quote_asset_match() -> None:
    symbol = symbol_fixture(base_asset="GBP", quote_asset="JPY")
    event = event_fixture(currency="JPY")

    result = NewsRelevanceService().score_event_for_symbol(event, symbol)

    assert result.relevance_score == Decimal("0.65")


def test_relevance_usd_macro_match() -> None:
    symbol = symbol_fixture()
    event = event_fixture(currency="USD")

    result = NewsRelevanceService().score_event_for_symbol(event, symbol)

    assert result.relevance_score == Decimal("0.70")
    assert result.relevance_reason == "usd_macro_event_matched_usd_pair"


def test_relevance_no_match() -> None:
    symbol = symbol_fixture()
    event = event_fixture(currency="JPY")

    result = NewsRelevanceService().score_event_for_symbol(event, symbol)

    assert result.relevance_score == Decimal("0.00")


def test_importance_scoring_defaults() -> None:
    assert IMPORTANCE_SCORES["critical"] == Decimal("1.00")
    assert IMPORTANCE_SCORES["high"] == Decimal("0.80")
    assert IMPORTANCE_SCORES["unknown"] == Decimal("0.30")


def test_time_proximity_scoring() -> None:
    service = correlation_service()
    run = run_fixture()
    near_event = event_fixture(event_time=run.start_time - timedelta(minutes=4))
    far_event = event_fixture(event_time=run.start_time - timedelta(minutes=20))

    near_score, near_minutes = service.time_proximity_score(run, near_event)
    far_score, far_minutes = service.time_proximity_score(run, far_event)

    assert near_score == Decimal("1.00")
    assert near_minutes == Decimal("4.0000")
    assert far_score == Decimal("0.35")
    assert far_minutes == Decimal("20.0000")


def test_movement_magnitude_scoring_with_feature_snapshot() -> None:
    service = correlation_service()
    score, metadata = service.magnitude_score(
        signal_fixture(pips_moved=Decimal("12")),
        features_fixture(),
    )

    assert score >= Decimal("0.75")
    assert metadata["featureSnapshot"] == "present"


def test_movement_magnitude_scoring_without_feature_snapshot() -> None:
    service = correlation_service()
    score, metadata = service.magnitude_score(signal_fixture(), None)

    assert score == Decimal("0.30")
    assert metadata["featureSnapshot"] == "missing"


def test_unknown_sentiment_uses_neutral_score() -> None:
    service = correlation_service()
    score, alignment, metadata = service.sentiment_score(
        signal_fixture(bias=SignalBias.BULLISH.value),
        event_fixture(sentiment="unknown"),
    )

    assert score == Decimal("0.50")
    assert alignment == DirectionAlignment.UNKNOWN
    assert metadata["handling"] == "neutral_score"


def test_correlation_label_thresholds() -> None:
    assert correlation_label(Decimal("0.2400")) == CorrelationLabel.NONE
    assert correlation_label(Decimal("0.2500")) == CorrelationLabel.WEAK
    assert correlation_label(Decimal("0.5000")) == CorrelationLabel.POSSIBLE
    assert correlation_label(Decimal("0.7500")) == CorrelationLabel.STRONG


def test_reason_text_uses_causation_safe_language() -> None:
    service = correlation_service()
    run = run_fixture()
    event = event_fixture(event_time=run.start_time - timedelta(minutes=4), currency="USD")
    score = service.score_event(
        signal=signal_fixture(bias=SignalBias.BULLISH.value, volatility_state="spike"),
        run=run,
        symbol=symbol_fixture(),
        features=features_fixture(),
        event=event,
    )

    reason = score.reason.lower()
    assert score.correlation_label in {CorrelationLabel.POSSIBLE, CorrelationLabel.STRONG}
    assert "possible correlation" in reason
    assert "definitely" not in reason
    assert "guaranteed" not in reason
    assert "confirmed reason" not in reason
    assert "trade because" not in reason
    assert "caused" not in reason


def correlation_service() -> NewsCorrelationService:
    return NewsCorrelationService(
        session=cast(AsyncSession, object()),
        settings=Settings(_env_file=None),
    )


def symbol_fixture(
    base_asset: str = "EUR",
    quote_asset: str = "USD",
) -> Symbol:
    return Symbol(
        id=uuid4(),
        symbol=f"{base_asset}{quote_asset}",
        display_name=f"{base_asset}/{quote_asset}",
        market_type=MarketType.FOREX.value,
        base_asset=base_asset,
        quote_asset=quote_asset,
        pip_size=Decimal("0.0001"),
        tick_size=Decimal("0.00001"),
        price_precision=5,
        quantity_precision=2,
        is_active=True,
    )


def run_fixture() -> AnalysisRun:
    return AnalysisRun(
        id=uuid4(),
        workspace_id=uuid4(),
        user_id=None,
        symbol_id=uuid4(),
        source_id=None,
        timeframe="1m",
        start_time=datetime(2026, 4, 29, 12, 30, tzinfo=UTC),
        end_time=datetime(2026, 4, 29, 12, 45, tzinfo=UTC),
        analysis_mode=AnalysisMode.HISTORICAL.value,
        include_partial_live_candle=False,
        include_news_correlation=True,
        include_ai_explanation=False,
        status=AnalysisRunStatus.COMPLETED.value,
        engine_version="test",
        rule_set_version="test",
    )


def signal_fixture(
    bias: str = SignalBias.BULLISH.value,
    pips_moved: Decimal | None = Decimal("10"),
    volatility_state: str = "expanding",
) -> Signal:
    return Signal(
        id=uuid4(),
        analysis_run_id=uuid4(),
        workspace_id=uuid4(),
        symbol_id=uuid4(),
        timeframe="1m",
        bias=bias,
        classification_status=SignalClassificationStatus.SIGNAL.value,
        confidence_score=Decimal("0.8000"),
        confidence_label=SignalConfidenceLabel.HIGH.value,
        pips_moved=pips_moved,
        tick_moved=Decimal("100"),
        movement_direction=bias,
        movement_quality="efficient",
        volatility_state=volatility_state,
        trend_state="short_term_uptrend",
        range_state="range_break",
        summary="Test signal",
    )


def event_fixture(
    symbol_id: UUID | None = None,
    currency: str | None = None,
    asset: str | None = None,
    event_time: datetime | None = None,
    sentiment: str = "unknown",
) -> NewsEvent:
    return NewsEvent(
        id=uuid4(),
        workspace_id=None,
        source="manual",
        event_type=NewsEventType.ECONOMIC_CALENDAR.value,
        title="USD CPI Release",
        event_time=event_time or datetime(2026, 4, 29, 12, 26, tzinfo=UTC),
        currency=currency,
        asset=asset,
        symbol_id=symbol_id,
        importance="high",
        sentiment=sentiment,
        raw_payload_json={},
    )


def features_fixture() -> dict[str, object]:
    return {
        "movement": {"movementQuality": "efficient"},
        "volatility": {"atrExpansionRatio": "1.50", "volatilityState": "expanding"},
    }
