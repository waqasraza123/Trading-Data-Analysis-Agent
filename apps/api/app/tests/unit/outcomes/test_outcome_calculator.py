from decimal import Decimal

from app.modules.outcomes.calculator import OutcomeCalculator
from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel
from app.modules.signals.models import SignalBias, SignalClassificationStatus
from app.modules.symbols.models import MarketType
from app.tests.unit.outcomes.factories import calculation_input, candle


def test_bullish_continuation_calculation() -> None:
    result = OutcomeCalculator().calculate(calculation_input())

    assert result.evaluation_status == OutcomeEvaluationStatus.EVALUATED
    assert result.outcome_label == OutcomeLabel.CONTINUATION
    assert result.max_favorable_move == Decimal("3")
    assert result.direction_followed is True


def test_bullish_reversal_calculation() -> None:
    result = OutcomeCalculator().calculate(
        calculation_input(
            candles=[
                candle(1, "100.2", "99.5", "99.8"),
                candle(2, "100.1", "97.8", "98.2"),
                candle(3, "99.0", "96.5", "97.0"),
            ]
        )
    )

    assert result.outcome_label == OutcomeLabel.REVERSAL
    assert result.reversal_detected is True


def test_bearish_continuation_calculation() -> None:
    result = OutcomeCalculator().calculate(
        calculation_input(
            bias=SignalBias.BEARISH,
            candles=[
                candle(1, "100.2", "99.2", "99.4"),
                candle(2, "99.5", "98.0", "98.6"),
                candle(3, "98.8", "97.2", "97.8"),
            ],
        )
    )

    assert result.outcome_label == OutcomeLabel.CONTINUATION
    assert result.direction_followed is True


def test_bearish_reversal_calculation() -> None:
    result = OutcomeCalculator().calculate(
        calculation_input(
            bias=SignalBias.BEARISH,
            candles=[
                candle(1, "100.6", "99.8", "100.3"),
                candle(2, "102.0", "100.1", "101.8"),
                candle(3, "103.5", "101.5", "103.0"),
            ],
        )
    )

    assert result.outcome_label == OutcomeLabel.REVERSAL
    assert result.reversal_detected is True


def test_neutral_no_signal_is_not_directional() -> None:
    result = OutcomeCalculator().calculate(
        calculation_input(
            bias=SignalBias.NEUTRAL,
            classification_status=SignalClassificationStatus.NO_SIGNAL,
        )
    )

    assert result.evaluation_status == OutcomeEvaluationStatus.SKIPPED_NOT_DIRECTIONAL
    assert result.outcome_label == OutcomeLabel.NOT_DIRECTIONAL
    assert result.direction_followed is None


def test_insufficient_future_candles() -> None:
    result = OutcomeCalculator().calculate(
        calculation_input(candles=[candle(1, "101", "100", "100.5")])
    )

    assert result.evaluation_status == OutcomeEvaluationStatus.INSUFFICIENT_FUTURE_DATA
    assert result.outcome_label == OutcomeLabel.INSUFFICIENT_DATA


def test_forex_pip_conversion() -> None:
    result = OutcomeCalculator().calculate(
        calculation_input(
            reference_price="1.1000",
            candles=[
                candle(1, "1.1010", "1.0998", "1.1005"),
                candle(2, "1.1020", "1.1004", "1.1014"),
                candle(3, "1.1030", "1.1012", "1.1022"),
            ],
        )
    )

    assert result.max_favorable_pips == Decimal("30")
    assert result.net_pips == Decimal("22")


def test_crypto_tick_conversion() -> None:
    result = OutcomeCalculator().calculate(
        calculation_input(market_type=MarketType.CRYPTO, pip_size=None, tick_size="0.50")
    )

    assert result.max_favorable_ticks == Decimal("6")
    assert result.net_ticks == Decimal("4.4")


def test_missing_pip_or_tick_metadata_degrades_gracefully() -> None:
    forex_result = OutcomeCalculator().calculate(calculation_input(pip_size=None))
    crypto_result = OutcomeCalculator().calculate(
        calculation_input(market_type=MarketType.CRYPTO, pip_size=None, tick_size=None)
    )

    assert forex_result.max_favorable_pips is None
    forex_warnings = forex_result.metadata_json.get("warnings")
    assert isinstance(forex_warnings, list)
    assert "missing_pip_size" in forex_warnings
    assert crypto_result.max_favorable_ticks is None
    crypto_warnings = crypto_result.metadata_json.get("warnings")
    assert isinstance(crypto_warnings, list)
    assert "missing_tick_size" in crypto_warnings


def test_no_follow_through_threshold_behavior() -> None:
    result = OutcomeCalculator().calculate(
        calculation_input(
            candles=[
                candle(1, "100.01", "99.99", "100.00"),
                candle(2, "100.02", "99.98", "100.00"),
                candle(3, "100.01", "99.99", "100.00"),
            ]
        )
    )

    assert result.outcome_label == OutcomeLabel.NO_FOLLOW_THROUGH
