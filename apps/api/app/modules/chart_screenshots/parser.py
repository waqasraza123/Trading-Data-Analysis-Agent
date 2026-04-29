from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.modules.chart_screenshots.models import ChartTrendDirection
from app.modules.chart_screenshots.schemas import ChartScreenshotCandle

CHART_SCREENSHOT_PARSER_NAME = "manual_chart_screenshot_extraction"
CHART_SCREENSHOT_PARSER_VERSION = "0.1.0"
MIN_DIRECTIONAL_MOVE = Decimal("0.001")


@dataclass(frozen=True)
class ChartTrendHypothesis:
    direction: ChartTrendDirection
    confidence: Decimal
    metrics_json: dict[str, object]
    warnings: list[str]


def build_trend_hypothesis(
    candles: list[ChartScreenshotCandle],
    extraction_confidence: Decimal,
) -> ChartTrendHypothesis:
    sorted_candles = sorted(candles, key=lambda candle: candle.timestamp)
    warnings: list[str] = []
    if len(sorted_candles) < 3:
        return ChartTrendHypothesis(
            direction=ChartTrendDirection.UNCLEAR,
            confidence=Decimal("0.0000"),
            metrics_json={"reason": "too_few_candles"},
            warnings=["At least three extracted candles are required for a trend hypothesis"],
        )

    first_close = sorted_candles[0].close
    last_close = sorted_candles[-1].close
    move_ratio = (last_close - first_close) / first_close
    close_deltas = [
        sorted_candles[index].close - sorted_candles[index - 1].close
        for index in range(1, len(sorted_candles))
    ]
    upward_steps = sum(1 for delta in close_deltas if delta > 0)
    downward_steps = sum(1 for delta in close_deltas if delta < 0)
    flat_steps = len(close_deltas) - upward_steps - downward_steps
    directional_steps = max(upward_steps, downward_steps)
    consistency = Decimal(directional_steps) / Decimal(len(close_deltas))
    magnitude = min(abs(move_ratio) * Decimal("20"), Decimal("1"))
    confidence = ((consistency * Decimal("0.60")) + (magnitude * Decimal("0.40")))
    confidence = (confidence * extraction_confidence).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )

    if abs(move_ratio) < MIN_DIRECTIONAL_MOVE:
        direction = ChartTrendDirection.NEUTRAL
    elif move_ratio > 0:
        direction = ChartTrendDirection.BULLISH
    else:
        direction = ChartTrendDirection.BEARISH

    if extraction_confidence < Decimal("0.5"):
        warnings.append("Extraction confidence is low; treat the trend hypothesis as provisional")
    if consistency < Decimal("0.5"):
        warnings.append("Extracted candle closes are mixed; trend direction is weak")

    return ChartTrendHypothesis(
        direction=direction,
        confidence=confidence,
        metrics_json={
            "firstClose": str(first_close),
            "lastClose": str(last_close),
            "moveRatio": str(move_ratio.quantize(Decimal("0.000001"))),
            "upwardSteps": upward_steps,
            "downwardSteps": downward_steps,
            "flatSteps": flat_steps,
            "closeConsistency": str(consistency.quantize(Decimal("0.0001"))),
        },
        warnings=warnings,
    )
