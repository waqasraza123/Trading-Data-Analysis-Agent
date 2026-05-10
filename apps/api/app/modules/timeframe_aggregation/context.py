from dataclasses import dataclass
from decimal import Decimal

from app.modules.candles.models import Candle
from app.modules.signals.models import Signal, SignalBias, SignalClassificationStatus
from app.modules.timeframe_aggregation.models import TimeframeAgreementLabel, TimeframeAlignment


@dataclass(frozen=True)
class TimeframeContextSnapshot:
    timeframe: str
    candle_count: int
    trend_direction: str
    range_behavior: str
    volatility_behavior: str
    latest_candle_direction: str
    start_timestamp: str | None
    end_timestamp: str | None

    def to_json(self) -> dict[str, object]:
        return {
            "timeframe": self.timeframe,
            "candleCount": self.candle_count,
            "trendDirection": self.trend_direction,
            "rangeBehavior": self.range_behavior,
            "volatilityBehavior": self.volatility_behavior,
            "latestCandleDirection": self.latest_candle_direction,
            "startTimestamp": self.start_timestamp,
            "endTimestamp": self.end_timestamp,
        }


@dataclass(frozen=True)
class MultiTimeframeContextResult:
    trend_alignment: TimeframeAlignment
    volatility_alignment: TimeframeAlignment
    range_alignment: TimeframeAlignment
    agreement_score: Decimal
    agreement_label: TimeframeAgreementLabel
    context_summary: str
    context_json: dict[str, object]
    warnings_json: list[dict[str, object]]


class MultiTimeframeContextEngine:
    def build(
        self,
        signal: Signal | None,
        snapshots: list[TimeframeContextSnapshot],
    ) -> MultiTimeframeContextResult:
        warnings = self.build_warnings(signal, snapshots)
        trend_alignment = self.resolve_trend_alignment(signal, snapshots)
        volatility_alignment = self.resolve_secondary_alignment(
            [snapshot.volatility_behavior for snapshot in snapshots],
            positive_values={"stable", "decreasing"},
            caution_values={"increasing"},
        )
        range_alignment = self.resolve_secondary_alignment(
            [snapshot.range_behavior for snapshot in snapshots],
            positive_values={"stable", "contracting"},
            caution_values={"expanding"},
        )
        agreement_score = self.score_agreement(signal, snapshots).quantize(Decimal("0.0001"))
        agreement_label = self.label_agreement(signal, snapshots, agreement_score)
        context_summary = self.summarize(
            signal=signal,
            snapshots=snapshots,
            trend_alignment=trend_alignment,
            agreement_label=agreement_label,
        )
        return MultiTimeframeContextResult(
            trend_alignment=trend_alignment,
            volatility_alignment=volatility_alignment,
            range_alignment=range_alignment,
            agreement_score=agreement_score,
            agreement_label=agreement_label,
            context_summary=context_summary,
            context_json={"timeframes": [snapshot.to_json() for snapshot in snapshots]},
            warnings_json=warnings,
        )

    def snapshot_from_candles(
        self, timeframe: str, candles: list[Candle]
    ) -> TimeframeContextSnapshot:
        ordered = sorted(candles, key=lambda candle: candle.timestamp)
        if len(ordered) < 2:
            return TimeframeContextSnapshot(
                timeframe=timeframe,
                candle_count=len(ordered),
                trend_direction="unclear",
                range_behavior="unclear",
                volatility_behavior="unclear",
                latest_candle_direction=self.latest_candle_direction(ordered),
                start_timestamp=ordered[0].timestamp.isoformat() if ordered else None,
                end_timestamp=ordered[-1].timestamp.isoformat() if ordered else None,
            )
        return TimeframeContextSnapshot(
            timeframe=timeframe,
            candle_count=len(ordered),
            trend_direction=self.trend_direction(ordered),
            range_behavior=self.range_behavior(ordered),
            volatility_behavior=self.volatility_behavior(ordered),
            latest_candle_direction=self.latest_candle_direction(ordered),
            start_timestamp=ordered[0].timestamp.isoformat(),
            end_timestamp=ordered[-1].timestamp.isoformat(),
        )

    def trend_direction(self, candles: list[Candle]) -> str:
        first_close = candles[0].close
        last_close = candles[-1].close
        if first_close <= 0:
            return "unclear"
        change_ratio = (last_close - first_close) / first_close
        if change_ratio >= Decimal("0.0010"):
            return "uptrend"
        if change_ratio <= Decimal("-0.0010"):
            return "downtrend"
        return "sideways"

    def range_behavior(self, candles: list[Candle]) -> str:
        if len(candles) < 4:
            return "unclear"
        midpoint = len(candles) // 2
        first_range = self.average_range(candles[:midpoint])
        second_range = self.average_range(candles[midpoint:])
        if first_range <= 0:
            return "unclear"
        ratio = (second_range - first_range) / first_range
        if ratio >= Decimal("0.1000"):
            return "expanding"
        if ratio <= Decimal("-0.1000"):
            return "contracting"
        return "stable"

    def volatility_behavior(self, candles: list[Candle]) -> str:
        if len(candles) < 4:
            return "unclear"
        midpoint = len(candles) // 2
        first_volatility = self.average_absolute_return(candles[:midpoint])
        second_volatility = self.average_absolute_return(candles[midpoint:])
        if first_volatility <= 0:
            return "unclear"
        ratio = (second_volatility - first_volatility) / first_volatility
        if ratio >= Decimal("0.1000"):
            return "increasing"
        if ratio <= Decimal("-0.1000"):
            return "decreasing"
        return "stable"

    def latest_candle_direction(self, candles: list[Candle]) -> str:
        if not candles:
            return "unclear"
        latest = candles[-1]
        if latest.close > latest.open:
            return "bullish"
        if latest.close < latest.open:
            return "bearish"
        return "neutral"

    def average_range(self, candles: list[Candle]) -> Decimal:
        if not candles:
            return Decimal("0")
        return sum((candle.high - candle.low for candle in candles), Decimal("0")) / Decimal(
            len(candles)
        )

    def average_absolute_return(self, candles: list[Candle]) -> Decimal:
        returns: list[Decimal] = []
        for previous, current in zip(candles, candles[1:], strict=False):
            if previous.close > 0:
                returns.append(abs((current.close - previous.close) / previous.close))
        if not returns:
            return Decimal("0")
        return sum(returns, Decimal("0")) / Decimal(len(returns))

    def resolve_trend_alignment(
        self,
        signal: Signal | None,
        snapshots: list[TimeframeContextSnapshot],
    ) -> TimeframeAlignment:
        if signal is None or signal.classification_status != SignalClassificationStatus.SIGNAL:
            return TimeframeAlignment.UNCLEAR
        if signal.bias not in {SignalBias.BULLISH, SignalBias.BEARISH}:
            return TimeframeAlignment.UNCLEAR
        aligned = 0
        conflicting = 0
        for snapshot in snapshots:
            alignment = self.single_trend_alignment(signal.bias, snapshot.trend_direction)
            if alignment == TimeframeAlignment.ALIGNED:
                aligned += 1
            if alignment == TimeframeAlignment.CONFLICTING:
                conflicting += 1
        if aligned and not conflicting:
            return TimeframeAlignment.ALIGNED
        if aligned and conflicting:
            return TimeframeAlignment.PARTIALLY_ALIGNED
        if conflicting:
            return TimeframeAlignment.CONFLICTING
        return TimeframeAlignment.UNCLEAR

    def single_trend_alignment(self, bias: str, trend_direction: str) -> TimeframeAlignment:
        if bias == SignalBias.BULLISH and trend_direction == "uptrend":
            return TimeframeAlignment.ALIGNED
        if bias == SignalBias.BEARISH and trend_direction == "downtrend":
            return TimeframeAlignment.ALIGNED
        if bias == SignalBias.BULLISH and trend_direction == "downtrend":
            return TimeframeAlignment.CONFLICTING
        if bias == SignalBias.BEARISH and trend_direction == "uptrend":
            return TimeframeAlignment.CONFLICTING
        return TimeframeAlignment.UNCLEAR

    def resolve_secondary_alignment(
        self,
        values: list[str],
        positive_values: set[str],
        caution_values: set[str],
    ) -> TimeframeAlignment:
        if not values or all(value == "unclear" for value in values):
            return TimeframeAlignment.UNCLEAR
        positive_count = sum(1 for value in values if value in positive_values)
        caution_count = sum(1 for value in values if value in caution_values)
        if positive_count and not caution_count:
            return TimeframeAlignment.ALIGNED
        if positive_count and caution_count:
            return TimeframeAlignment.PARTIALLY_ALIGNED
        if caution_count:
            return TimeframeAlignment.CONFLICTING
        return TimeframeAlignment.UNCLEAR

    def score_agreement(
        self, signal: Signal | None, snapshots: list[TimeframeContextSnapshot]
    ) -> Decimal:
        if signal is None or signal.classification_status != SignalClassificationStatus.SIGNAL:
            return Decimal("0")
        if signal.bias not in {SignalBias.BULLISH, SignalBias.BEARISH}:
            return Decimal("0")
        scored = [
            self.single_trend_alignment(signal.bias, snapshot.trend_direction)
            for snapshot in snapshots
            if snapshot.trend_direction != "unclear"
        ]
        if not scored:
            return Decimal("0")
        points = Decimal("0")
        for alignment in scored:
            if alignment == TimeframeAlignment.ALIGNED:
                points += Decimal("1")
            elif alignment == TimeframeAlignment.UNCLEAR:
                points += Decimal("0.5")
        return points / Decimal(len(scored))

    def label_agreement(
        self,
        signal: Signal | None,
        snapshots: list[TimeframeContextSnapshot],
        agreement_score: Decimal,
    ) -> TimeframeAgreementLabel:
        if (
            not snapshots
            or signal is None
            or signal.classification_status != SignalClassificationStatus.SIGNAL
        ):
            return TimeframeAgreementLabel.INSUFFICIENT_CONTEXT
        if agreement_score >= Decimal("0.7500"):
            return TimeframeAgreementLabel.STRONG
        if agreement_score >= Decimal("0.5500"):
            return TimeframeAgreementLabel.ACCEPTABLE
        if agreement_score >= Decimal("0.3500"):
            return TimeframeAgreementLabel.MIXED
        return TimeframeAgreementLabel.CONFLICTING

    def build_warnings(
        self,
        signal: Signal | None,
        snapshots: list[TimeframeContextSnapshot],
    ) -> list[dict[str, object]]:
        warnings: list[dict[str, object]] = []
        if not snapshots:
            warnings.append(
                {
                    "code": "insufficient_context",
                    "message": "No higher-timeframe final candles were available",
                }
            )
        for snapshot in snapshots:
            if snapshot.candle_count < 4:
                warnings.append(
                    {
                        "code": "thin_context_window",
                        "message": "Higher-timeframe context has limited final candles",
                        "timeframe": snapshot.timeframe,
                        "candleCount": snapshot.candle_count,
                    }
                )
        if signal is None:
            warnings.append(
                {
                    "code": "signal_not_available",
                    "message": "No persisted signal was available for agreement comparison",
                }
            )
        return warnings

    def summarize(
        self,
        signal: Signal | None,
        snapshots: list[TimeframeContextSnapshot],
        trend_alignment: TimeframeAlignment,
        agreement_label: TimeframeAgreementLabel,
    ) -> str:
        if not snapshots:
            return "No higher-timeframe context was available from final candles."
        if signal is None or signal.classification_status != SignalClassificationStatus.SIGNAL:
            return "Higher-timeframe context was stored without changing any signal classification."
        return (
            f"Higher-timeframe trend context is {trend_alignment.value}; "
            f"timeframe agreement is {agreement_label.value}."
        )
