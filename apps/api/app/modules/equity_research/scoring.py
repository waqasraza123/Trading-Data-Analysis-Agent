from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.config import Settings
from app.modules.candles.models import Candle
from app.modules.equity_research.models import (
    EquityCatalystContext,
    EquitySwingCandidateStatus,
    EquitySwingDirectionalBias,
    EquitySwingSetupQualityLabel,
    EquitySwingSetupType,
)
from app.modules.equity_research.repository import EquityResearchArtifacts
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.setup_context.models import SetupContext

ZERO = Decimal("0")
ONE = Decimal("1")
FOUR_PLACES = Decimal("0.0001")
MIN_CANDLES = 20
COMPONENT_WEIGHTS = {
    "liquidity": Decimal("0.12"),
    "volume": Decimal("0.12"),
    "trend_quality": Decimal("0.18"),
    "pullback_quality": Decimal("0.14"),
    "relative_strength": Decimal("0.12"),
    "momentum": Decimal("0.14"),
    "volatility": Decimal("0.08"),
    "catalyst": Decimal("0.05"),
    "data_quality": Decimal("0.05"),
}


@dataclass(frozen=True)
class SwingScanProfile:
    key: str
    setup_types: tuple[EquitySwingSetupType, ...]
    minimum_setup_score: Decimal
    minimum_liquidity_score: Decimal
    minimum_trend_score: Decimal
    minimum_relative_strength_score: Decimal
    stale_tolerance: str


@dataclass(frozen=True)
class EquitySwingScoringInput:
    ticker: str
    timeframe: str
    candles: list[Candle]
    artifacts: EquityResearchArtifacts = field(default_factory=EquityResearchArtifacts)
    average_volume: Decimal | None = None
    min_average_volume: Decimal = Decimal("500000")
    min_setup_score: Decimal = Decimal("0.6000")
    strong_setup_score: Decimal = Decimal("0.7500")
    profile: SwingScanProfile | None = None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source_id_provided: bool = False


@dataclass(frozen=True)
class EquitySwingScoreDraft:
    candidate_status: EquitySwingCandidateStatus
    setup_type: EquitySwingSetupType
    directional_bias: EquitySwingDirectionalBias
    setup_quality_score: Decimal
    setup_quality_label: EquitySwingSetupQualityLabel
    liquidity_score: Decimal | None
    volume_score: Decimal | None
    trend_quality_score: Decimal | None
    pullback_quality_score: Decimal | None
    relative_strength_score: Decimal | None
    momentum_score: Decimal | None
    volatility_score: Decimal | None
    catalyst_score: Decimal | None
    confidence_context_json: dict[str, object]
    evidence_json: list[dict[str, object]]
    risk_notes_json: list[dict[str, object]]


SCAN_PROFILES: dict[str, SwingScanProfile] = {
    "continuation_momentum": SwingScanProfile(
        key="continuation_momentum",
        setup_types=(EquitySwingSetupType.CONTINUATION, EquitySwingSetupType.MOMENTUM),
        minimum_setup_score=Decimal("0.6000"),
        minimum_liquidity_score=Decimal("0.4500"),
        minimum_trend_score=Decimal("0.5500"),
        minimum_relative_strength_score=Decimal("0.3500"),
        stale_tolerance="standard",
    ),
    "constructive_pullback": SwingScanProfile(
        key="constructive_pullback",
        setup_types=(EquitySwingSetupType.PULLBACK, EquitySwingSetupType.CONTINUATION),
        minimum_setup_score=Decimal("0.5800"),
        minimum_liquidity_score=Decimal("0.4500"),
        minimum_trend_score=Decimal("0.5500"),
        minimum_relative_strength_score=Decimal("0.3500"),
        stale_tolerance="standard",
    ),
    "breakout_retest": SwingScanProfile(
        key="breakout_retest",
        setup_types=(EquitySwingSetupType.BREAKOUT_RETEST, EquitySwingSetupType.RANGE_BREAK),
        minimum_setup_score=Decimal("0.6000"),
        minimum_liquidity_score=Decimal("0.4500"),
        minimum_trend_score=Decimal("0.5000"),
        minimum_relative_strength_score=Decimal("0.3500"),
        stale_tolerance="standard",
    ),
    "reversal_watch": SwingScanProfile(
        key="reversal_watch",
        setup_types=(EquitySwingSetupType.REVERSAL_WATCH,),
        minimum_setup_score=Decimal("0.5200"),
        minimum_liquidity_score=Decimal("0.4000"),
        minimum_trend_score=Decimal("0.2500"),
        minimum_relative_strength_score=Decimal("0.2500"),
        stale_tolerance="standard",
    ),
    "avoid_chop_or_stale": SwingScanProfile(
        key="avoid_chop_or_stale",
        setup_types=(EquitySwingSetupType.NO_CLEAR_SETUP,),
        minimum_setup_score=Decimal("0.3500"),
        minimum_liquidity_score=Decimal("0.0000"),
        minimum_trend_score=Decimal("0.0000"),
        minimum_relative_strength_score=Decimal("0.0000"),
        stale_tolerance="strict",
    ),
}


class EquitySwingScorer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def profile(self, key: str) -> SwingScanProfile:
        return SCAN_PROFILES.get(key, SCAN_PROFILES["continuation_momentum"])

    def score(self, payload: EquitySwingScoringInput) -> EquitySwingScoreDraft:
        candles = sorted(payload.candles, key=lambda candle: candle.timestamp)
        evidence: list[dict[str, object]] = []
        risk_notes: list[dict[str, object]] = []
        if len(candles) < MIN_CANDLES:
            return insufficient_context(payload, candles)
        if not payload.source_id_provided:
            risk_notes.append(
                {
                    "code": "source_not_pinned",
                    "severity": "low",
                    "message": "Scan used stored final candles without a pinned source.",
                }
            )
        stale = data_is_stale(candles[-1], payload.timeframe, payload.evaluated_at)
        if stale:
            risk_notes.append(
                {
                    "code": "data_stale",
                    "severity": "high",
                    "message": "Latest final candle is outside the freshness tolerance.",
                }
            )
        component_scores = {
            "liquidity": liquidity_score(
                candles,
                resolved_average_volume(payload),
                payload.min_average_volume,
            ),
            "volume": volume_score(candles),
            "trend_quality": trend_quality_score(candles, payload.artifacts.indicator_snapshot),
            "pullback_quality": pullback_quality_score(candles, payload.artifacts.setup_context),
            "relative_strength": relative_strength_score(payload.artifacts),
            "momentum": momentum_score(candles, payload.artifacts.indicator_snapshot),
            "volatility": volatility_score(candles, payload.artifacts.indicator_snapshot),
            "catalyst": catalyst_score(payload.artifacts.catalysts or []),
            "data_quality": data_quality_score(payload.artifacts, stale),
        }
        setup_score = decimal_score(
            sum(component_scores[name] * weight for name, weight in COMPONENT_WEIGHTS.items())
        )
        setup_type = resolve_setup_type(payload.profile, component_scores, payload.artifacts)
        directional_bias = resolve_directional_bias(candles, payload.artifacts.setup_context)
        evidence.extend(build_evidence(payload, component_scores, setup_type, directional_bias))
        risk_notes.extend(build_component_risks(payload, component_scores))
        setup_label = setup_quality_label(
            setup_score,
            payload.min_setup_score,
            payload.strong_setup_score,
            risk_notes,
        )
        candidate_status = candidate_status_for(
            setup_score=setup_score,
            setup_label=setup_label,
            setup_type=setup_type,
            stale=stale,
            profile=payload.profile,
            component_scores=component_scores,
        )
        confidence_context = {
            "componentScores": {key: str(value) for key, value in component_scores.items()},
            "profileKey": payload.profile.key if payload.profile is not None else None,
            "latestFinalCandleTime": candles[-1].timestamp.isoformat(),
            "candleCount": len(candles),
            "scoringVersion": self.settings.equity_research_version,
            "enrichment": enrichment_context(payload),
        }
        return EquitySwingScoreDraft(
            candidate_status=candidate_status,
            setup_type=setup_type,
            directional_bias=directional_bias,
            setup_quality_score=setup_score,
            setup_quality_label=setup_label,
            liquidity_score=component_scores["liquidity"],
            volume_score=component_scores["volume"],
            trend_quality_score=component_scores["trend_quality"],
            pullback_quality_score=component_scores["pullback_quality"],
            relative_strength_score=component_scores["relative_strength"],
            momentum_score=component_scores["momentum"],
            volatility_score=component_scores["volatility"],
            catalyst_score=component_scores["catalyst"],
            confidence_context_json=confidence_context,
            evidence_json=evidence,
            risk_notes_json=risk_notes,
        )


def insufficient_context(
    payload: EquitySwingScoringInput,
    candles: list[Candle],
) -> EquitySwingScoreDraft:
    return EquitySwingScoreDraft(
        candidate_status=EquitySwingCandidateStatus.INSUFFICIENT_DATA,
        setup_type=EquitySwingSetupType.NO_CLEAR_SETUP,
        directional_bias=EquitySwingDirectionalBias.UNCLEAR,
        setup_quality_score=ZERO,
        setup_quality_label=EquitySwingSetupQualityLabel.INSUFFICIENT_CONTEXT,
        liquidity_score=None,
        volume_score=None,
        trend_quality_score=None,
        pullback_quality_score=None,
        relative_strength_score=None,
        momentum_score=None,
        volatility_score=None,
        catalyst_score=None,
        confidence_context_json={
            "profileKey": payload.profile.key if payload.profile is not None else None,
            "candleCount": len(candles),
            "scoringVersion": "insufficient_context",
        },
        evidence_json=[
            {
                "type": "data_coverage",
                "message": (
                    "Stored final candles are insufficient for equity swing research scoring."
                ),
                "value": len(candles),
            }
        ],
        risk_notes_json=[
            {
                "code": "insufficient_final_candles",
                "severity": "high",
                "message": "More final candles are needed before setup quality can be reviewed.",
            }
        ],
    )


def liquidity_score(
    candles: list[Candle],
    average_volume: Decimal | None,
    min_average_volume: Decimal,
) -> Decimal:
    volume_values = [Decimal(candle.volume) for candle in candles if candle.volume is not None]
    resolved_average = average_volume
    if resolved_average is None and volume_values:
        resolved_average = sum(volume_values, ZERO) / Decimal(len(volume_values))
    if resolved_average is None:
        return Decimal("0.4500")
    if min_average_volume <= 0:
        return Decimal("0.7500")
    return decimal_score(resolved_average / min_average_volume)


def resolved_average_volume(payload: EquitySwingScoringInput) -> Decimal | None:
    if payload.average_volume is not None:
        return payload.average_volume
    if (
        payload.artifacts.fundamentals is not None
        and payload.artifacts.fundamentals.average_volume is not None
    ):
        return Decimal(payload.artifacts.fundamentals.average_volume)
    if (
        payload.artifacts.symbol_metadata is not None
        and payload.artifacts.symbol_metadata.average_volume is not None
    ):
        return Decimal(payload.artifacts.symbol_metadata.average_volume)
    return None


def enrichment_context(payload: EquitySwingScoringInput) -> dict[str, object]:
    return {
        "metadataAvailable": payload.artifacts.symbol_metadata is not None,
        "fundamentalsAvailable": payload.artifacts.fundamentals is not None,
        "earningsEventsAvailable": bool(payload.artifacts.earnings_events),
    }


def volume_score(candles: list[Candle]) -> Decimal:
    volume_values = [Decimal(candle.volume) for candle in candles if candle.volume is not None]
    if len(volume_values) < 10:
        return Decimal("0.4500")
    recent = average_decimal(volume_values[-5:])
    baseline = average_decimal(volume_values[:-5] or volume_values)
    if baseline <= 0:
        return Decimal("0.4500")
    ratio = recent / baseline
    if ratio >= Decimal("1.50"):
        return Decimal("0.9500")
    if ratio >= Decimal("1.15"):
        return Decimal("0.8000")
    if ratio >= Decimal("0.85"):
        return Decimal("0.6200")
    return Decimal("0.3500")


def trend_quality_score(candles: list[Candle], indicators: IndicatorSnapshot | None) -> Decimal:
    closes = [Decimal(candle.close) for candle in candles]
    latest = closes[-1]
    sma20 = average_decimal(closes[-20:])
    sma50 = average_decimal(closes[-50:]) if len(closes) >= 50 else sma20
    score = Decimal("0.5000")
    if latest > sma20:
        score += Decimal("0.1500")
    if sma20 >= sma50:
        score += Decimal("0.1500")
    if closes[-1] > closes[-10]:
        score += Decimal("0.1000")
    if higher_low_structure(candles):
        score += Decimal("0.1000")
    alignment = indicator_value(indicators, "ema", "alignment")
    if alignment == "bullish_alignment":
        score += Decimal("0.1000")
    if alignment == "bearish_alignment":
        score -= Decimal("0.1000")
    return decimal_score(score)


def pullback_quality_score(candles: list[Candle], setup_context: SetupContext | None) -> Decimal:
    closes = [Decimal(candle.close) for candle in candles]
    recent_high = max(closes[-20:])
    latest = closes[-1]
    if recent_high <= 0:
        return Decimal("0.4500")
    drawdown = (recent_high - latest) / recent_high
    score = Decimal("0.4500")
    if Decimal("0.0200") <= drawdown <= Decimal("0.1200"):
        score = Decimal("0.7600")
    elif drawdown < Decimal("0.0200"):
        score = Decimal("0.6200")
    elif drawdown <= Decimal("0.1800"):
        score = Decimal("0.5200")
    else:
        score = Decimal("0.2500")
    if setup_context is not None and setup_context.setup_quality_label in {
        "strong_context",
        "acceptable_context",
    }:
        score += Decimal("0.1000")
    return decimal_score(score)


def relative_strength_score(artifacts: EquityResearchArtifacts) -> Decimal:
    memory = artifacts.market_memory
    if memory is None:
        return Decimal("0.5000")
    if memory.cross_asset_label in {"aligned", "strong_alignment", "relative_strength"}:
        return Decimal("0.7500")
    if memory.cross_asset_label in {"divergent", "conflicted"}:
        return Decimal("0.3500")
    return Decimal("0.5000")


def momentum_score(candles: list[Candle], indicators: IndicatorSnapshot | None) -> Decimal:
    closes = [Decimal(candle.close) for candle in candles]
    base = closes[-20]
    if base <= 0:
        price_score = Decimal("0.4500")
    else:
        change = (closes[-1] - base) / base
        price_score = decimal_score(Decimal("0.5000") + (change * Decimal("3.0")))
    rsi_state = indicator_value(indicators, "rsi", "state")
    macd_state = indicator_value(indicators, "macd", "state")
    if rsi_state == "bullish_momentum":
        price_score += Decimal("0.0800")
    if rsi_state == "bearish_momentum":
        price_score -= Decimal("0.0800")
    if macd_state == "bullish":
        price_score += Decimal("0.0600")
    if macd_state == "bearish":
        price_score -= Decimal("0.0600")
    return decimal_score(price_score)


def volatility_score(candles: list[Candle], indicators: IndicatorSnapshot | None) -> Decimal:
    atr_state = indicator_value(indicators, "atr", "state")
    if atr_state == "normal":
        return Decimal("0.8000")
    if atr_state == "expanded":
        return Decimal("0.5200")
    if atr_state == "compressed":
        return Decimal("0.6500")
    ranges = [
        (Decimal(candle.high) - Decimal(candle.low)) / Decimal(candle.close)
        for candle in candles
        if candle.close > 0
    ]
    if not ranges:
        return Decimal("0.4500")
    average_range = average_decimal(ranges[-14:])
    if Decimal("0.0100") <= average_range <= Decimal("0.0600"):
        return Decimal("0.7800")
    if average_range < Decimal("0.0100"):
        return Decimal("0.5200")
    return Decimal("0.3500")


def catalyst_score(catalysts: list[EquityCatalystContext]) -> Decimal:
    if not catalysts:
        return Decimal("0.4500")
    importance_scores = {
        "high": Decimal("0.8500"),
        "medium": Decimal("0.6500"),
        "low": Decimal("0.5200"),
        "unknown": Decimal("0.5000"),
    }
    return max(
        importance_scores.get(catalyst.importance, Decimal("0.5000")) for catalyst in catalysts
    )


def data_quality_score(artifacts: EquityResearchArtifacts, stale: bool) -> Decimal:
    if stale:
        return Decimal("0.1500")
    if artifacts.market_memory is not None:
        label_score = {
            "strong": Decimal("0.9500"),
            "acceptable": Decimal("0.8000"),
            "degraded": Decimal("0.5000"),
            "poor": Decimal("0.2500"),
            "insufficient": Decimal("0.1500"),
            "unknown": Decimal("0.5000"),
        }.get(artifacts.market_memory.data_quality_label, Decimal("0.5000"))
        return label_score
    if artifacts.data_quality_run is not None:
        return decimal_score(Decimal(artifacts.data_quality_run.quality_score))
    return Decimal("0.6500")


def resolve_setup_type(
    profile: SwingScanProfile | None,
    component_scores: dict[str, Decimal],
    artifacts: EquityResearchArtifacts,
) -> EquitySwingSetupType:
    if profile is not None and profile.key == "reversal_watch":
        return EquitySwingSetupType.REVERSAL_WATCH
    if profile is not None and profile.key == "breakout_retest":
        return EquitySwingSetupType.BREAKOUT_RETEST
    if profile is not None and profile.key == "constructive_pullback":
        return EquitySwingSetupType.PULLBACK
    setup_context = artifacts.setup_context
    if setup_context is not None and setup_context.avoid_reasons_json:
        return EquitySwingSetupType.NO_CLEAR_SETUP
    if component_scores["momentum"] >= Decimal("0.7200"):
        return EquitySwingSetupType.MOMENTUM
    if component_scores["trend_quality"] >= Decimal("0.6200"):
        return EquitySwingSetupType.CONTINUATION
    return EquitySwingSetupType.NO_CLEAR_SETUP


def resolve_directional_bias(
    candles: list[Candle],
    setup_context: SetupContext | None,
) -> EquitySwingDirectionalBias:
    if setup_context is not None:
        try:
            return EquitySwingDirectionalBias(setup_context.directional_bias)
        except ValueError:
            pass
    closes = [Decimal(candle.close) for candle in candles]
    if closes[-1] > average_decimal(closes[-20:]):
        return EquitySwingDirectionalBias.BULLISH
    if closes[-1] < average_decimal(closes[-20:]):
        return EquitySwingDirectionalBias.BEARISH
    return EquitySwingDirectionalBias.UNCLEAR


def setup_quality_label(
    score: Decimal,
    min_setup_score: Decimal,
    strong_setup_score: Decimal,
    risk_notes: list[dict[str, object]],
) -> EquitySwingSetupQualityLabel:
    if any(note.get("code") == "data_stale" for note in risk_notes):
        return EquitySwingSetupQualityLabel.REVIEW_REQUIRED
    if score >= strong_setup_score:
        return EquitySwingSetupQualityLabel.STRONG_CONTEXT
    if score >= min_setup_score:
        return EquitySwingSetupQualityLabel.ACCEPTABLE_CONTEXT
    if score >= Decimal("0.4500"):
        return EquitySwingSetupQualityLabel.MIXED_CONTEXT
    if score >= Decimal("0.3500"):
        return EquitySwingSetupQualityLabel.REVIEW_REQUIRED
    return EquitySwingSetupQualityLabel.AVOID_CONDITION


def candidate_status_for(
    setup_score: Decimal,
    setup_label: EquitySwingSetupQualityLabel,
    setup_type: EquitySwingSetupType,
    stale: bool,
    profile: SwingScanProfile | None,
    component_scores: dict[str, Decimal],
) -> EquitySwingCandidateStatus:
    if stale:
        return EquitySwingCandidateStatus.STALE_DATA
    if setup_label == EquitySwingSetupQualityLabel.AVOID_CONDITION:
        return EquitySwingCandidateStatus.AVOID
    if setup_type == EquitySwingSetupType.NO_CLEAR_SETUP:
        return EquitySwingCandidateStatus.AVOID
    if profile is not None and profile.key == "reversal_watch":
        return EquitySwingCandidateStatus.NEEDS_CONFIRMATION
    if profile is not None and setup_score < profile.minimum_setup_score:
        return EquitySwingCandidateStatus.NEEDS_CONFIRMATION
    if component_scores["trend_quality"] < Decimal("0.3500") and component_scores[
        "momentum"
    ] > Decimal("0.6500"):
        return EquitySwingCandidateStatus.CONFLICTED
    if setup_label in {
        EquitySwingSetupQualityLabel.STRONG_CONTEXT,
        EquitySwingSetupQualityLabel.ACCEPTABLE_CONTEXT,
    }:
        return EquitySwingCandidateStatus.CANDIDATE
    return EquitySwingCandidateStatus.NEEDS_CONFIRMATION


def build_evidence(
    payload: EquitySwingScoringInput,
    component_scores: dict[str, Decimal],
    setup_type: EquitySwingSetupType,
    directional_bias: EquitySwingDirectionalBias,
) -> list[dict[str, object]]:
    return [
        {
            "type": "setup_profile",
            "message": (
                f"{payload.profile.key if payload.profile else 'equity'} profile produced "
                "a deterministic scan result."
            ),
            "value": setup_type.value,
        },
        {
            "type": "directional_bias",
            "message": f"Directional context is {directional_bias.value}.",
            "value": directional_bias.value,
        },
        {
            "type": "trend_quality",
            "message": "Trend structure contributed to setup quality.",
            "value": str(component_scores["trend_quality"]),
        },
        {
            "type": "volume_context",
            "message": "Recent volume was compared with stored candle baseline volume.",
            "value": str(component_scores["volume"]),
        },
        {
            "type": "catalyst_context",
            "message": "Persisted catalyst context was included when available.",
            "value": str(component_scores["catalyst"]),
        },
        {
            "type": "liquidity_context",
            "message": average_volume_evidence_message(payload),
            "value": str(component_scores["liquidity"]),
        },
        {
            "type": "earnings_context",
            "message": earnings_evidence_message(payload),
            "value": len(payload.artifacts.earnings_events or []),
        },
        {
            "type": "fundamentals_context",
            "message": fundamentals_evidence_message(payload),
            "value": payload.artifacts.fundamentals is not None,
        },
    ]


def build_component_risks(
    payload: EquitySwingScoringInput,
    component_scores: dict[str, Decimal],
) -> list[dict[str, object]]:
    risks: list[dict[str, object]] = []
    if component_scores["liquidity"] < Decimal("0.4000"):
        risks.append(
            {
                "code": "liquidity_context_weak",
                "severity": "medium",
                "message": "Liquidity context is below the configured review threshold.",
            }
        )
    if component_scores["relative_strength"] == Decimal("0.5000"):
        risks.append(
            {
                "code": "relative_strength_unknown",
                "severity": "low",
                "message": "Relative strength context was unavailable or neutral.",
            }
        )
    if payload.artifacts.setup_context is None:
        risks.append(
            {
                "code": "setup_context_missing",
                "severity": "low",
                "message": "Existing setup context was not available for this candidate.",
            }
        )
    return risks


def average_volume_evidence_message(payload: EquitySwingScoringInput) -> str:
    if resolved_average_volume(payload) is not None:
        return "Average volume context available."
    return "Average volume context unavailable."


def earnings_evidence_message(payload: EquitySwingScoringInput) -> str:
    if payload.artifacts.earnings_events:
        return "Upcoming earnings context available."
    return "Upcoming earnings context unavailable."


def fundamentals_evidence_message(payload: EquitySwingScoringInput) -> str:
    if payload.artifacts.fundamentals is not None:
        return "Fundamentals context available."
    return "Fundamentals context unavailable."


def indicator_value(snapshot: IndicatorSnapshot | None, section: str, key: str) -> object | None:
    if snapshot is None:
        return None
    section_value = snapshot.indicators_json.get(section)
    if not isinstance(section_value, dict):
        return None
    return section_value.get(key)


def data_is_stale(candle: Candle, timeframe: str, evaluated_at: datetime) -> bool:
    tolerance = {
        "1m": timedelta(minutes=15),
        "5m": timedelta(minutes=45),
        "15m": timedelta(hours=2),
        "30m": timedelta(hours=4),
        "1h": timedelta(days=1),
        "4h": timedelta(days=2),
        "1d": timedelta(days=7),
    }.get(timeframe, timedelta(days=7))
    return evaluated_at - candle.timestamp > tolerance


def higher_low_structure(candles: list[Candle]) -> bool:
    if len(candles) < 10:
        return False
    first_window_low = min(Decimal(candle.low) for candle in candles[-10:-5])
    second_window_low = min(Decimal(candle.low) for candle in candles[-5:])
    return second_window_low >= first_window_low


def average_decimal(values: list[Decimal]) -> Decimal:
    if not values:
        return ZERO
    return sum(values, ZERO) / Decimal(len(values))


def decimal_score(value: Decimal) -> Decimal:
    return clamp(value).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def clamp(value: Decimal) -> Decimal:
    if value < ZERO:
        return ZERO
    if value > ONE:
        return ONE
    return value
