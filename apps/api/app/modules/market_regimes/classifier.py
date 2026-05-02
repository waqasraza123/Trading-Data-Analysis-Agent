from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.market_regimes.models import (
    DataQualityLabel,
    RangeRegime,
    RegimeConfidenceLabel,
    TrendRegime,
    VolatilityRegime,
)
from app.modules.patterns.models import PatternCandidate
from app.modules.signals.models import Signal


@dataclass(frozen=True)
class MarketRegimeClassificationInput:
    features_json: dict[str, Any] | None
    indicators_json: dict[str, Any] | None
    signal: Signal | None
    pattern_candidates: list[PatternCandidate]
    min_confidence: Decimal
    strong_data_quality: Decimal
    acceptable_data_quality: Decimal


@dataclass(frozen=True)
class MarketRegimeClassificationResult:
    trend_regime: TrendRegime
    volatility_regime: VolatilityRegime
    range_regime: RangeRegime
    liquidity_regime: str | None
    data_quality_label: DataQualityLabel
    confidence_score: Decimal
    confidence_label: RegimeConfidenceLabel
    summary: str
    feature_inputs_json: dict[str, Any]
    indicator_inputs_json: dict[str, Any]
    warnings_json: list[dict[str, object]]
    metadata_json: dict[str, object]


class MarketRegimeClassifier:
    def classify(
        self,
        classification_input: MarketRegimeClassificationInput,
    ) -> MarketRegimeClassificationResult:
        features = classification_input.features_json or {}
        indicators = classification_input.indicators_json or {}
        warnings: list[dict[str, object]] = []
        feature_trend = self.feature_trend_regime(features)
        indicator_trend = self.indicator_trend_regime(indicators)
        trend_regime, trend_agreement = self.resolve_trend(feature_trend, indicator_trend, warnings)
        volatility_regime = self.resolve_volatility(features, indicators, warnings)
        range_regime = self.resolve_range(
            features,
            classification_input.signal,
            classification_input.pattern_candidates,
            warnings,
        )
        data_quality_label, data_quality_score = self.resolve_data_quality(
            features,
            classification_input.strong_data_quality,
            classification_input.acceptable_data_quality,
            warnings,
        )
        completeness_score = self.feature_completeness_score(features, indicators)
        pattern_signal_score = self.pattern_signal_agreement_score(
            range_regime,
            classification_input.signal,
            classification_input.pattern_candidates,
        )
        raw_confidence = (
            (completeness_score * Decimal("0.30"))
            + (trend_agreement * Decimal("0.25"))
            + (pattern_signal_score * Decimal("0.20"))
            + (data_quality_score * Decimal("0.25"))
        )
        confidence_score = clamp(raw_confidence).quantize(Decimal("0.0001"))
        if confidence_score < classification_input.min_confidence:
            warnings.append(
                {
                    "code": "below_minimum_confidence",
                    "message": "Regime confidence is below the configured minimum confidence.",
                }
            )
        confidence_label = self.confidence_label(confidence_score)
        feature_inputs_json = self.feature_inputs(features)
        indicator_inputs_json = self.indicator_inputs(indicators)
        metadata_json = {
            "classifier": "deterministic_market_regime",
            "featureCompletenessScore": str(completeness_score.quantize(Decimal("0.0001"))),
            "indicatorAgreementScore": str(trend_agreement.quantize(Decimal("0.0001"))),
            "patternSignalAgreementScore": str(pattern_signal_score.quantize(Decimal("0.0001"))),
            "dataQualityScore": str(data_quality_score.quantize(Decimal("0.0001"))),
            "signalId": str(classification_input.signal.id) if classification_input.signal else None,
            "patternCandidateCount": len(classification_input.pattern_candidates),
            "selectedPatternCandidateId": self.selected_pattern_candidate_id(
                classification_input.pattern_candidates
            ),
        }
        return MarketRegimeClassificationResult(
            trend_regime=trend_regime,
            volatility_regime=volatility_regime,
            range_regime=range_regime,
            liquidity_regime=None,
            data_quality_label=data_quality_label,
            confidence_score=confidence_score,
            confidence_label=confidence_label,
            summary=self.summary(
                trend_regime,
                volatility_regime,
                range_regime,
                data_quality_label,
                confidence_label,
            ),
            feature_inputs_json=feature_inputs_json,
            indicator_inputs_json=indicator_inputs_json,
            warnings_json=warnings,
            metadata_json=metadata_json,
        )

    def feature_trend_regime(self, features: dict[str, Any]) -> TrendRegime:
        trend = read_mapping(features, "trend")
        state = read_text(trend, "trendState")
        if state in {"short_term_uptrend", "uptrend"}:
            return TrendRegime.UPTREND
        if state in {"short_term_downtrend", "downtrend"}:
            return TrendRegime.DOWNTREND
        if state in {"mixed_or_sideways", "sideways", "rangebound"}:
            return TrendRegime.SIDEWAYS
        higher_highs = read_int(trend, "higherHighsCount")
        higher_lows = read_int(trend, "higherLowsCount")
        lower_highs = read_int(trend, "lowerHighsCount")
        lower_lows = read_int(trend, "lowerLowsCount")
        bullish_structure = higher_highs + higher_lows
        bearish_structure = lower_highs + lower_lows
        if bullish_structure > bearish_structure and bullish_structure > 0:
            return TrendRegime.UPTREND
        if bearish_structure > bullish_structure and bearish_structure > 0:
            return TrendRegime.DOWNTREND
        if bullish_structure or bearish_structure:
            return TrendRegime.SIDEWAYS
        return TrendRegime.UNCLEAR

    def indicator_trend_regime(self, indicators: dict[str, Any]) -> TrendRegime:
        ema = read_mapping(indicators, "ema")
        alignment = read_text(ema, "alignment")
        if alignment == "bullish_alignment":
            return TrendRegime.UPTREND
        if alignment == "bearish_alignment":
            return TrendRegime.DOWNTREND
        if alignment == "mixed":
            return TrendRegime.MIXED
        return TrendRegime.UNCLEAR

    def resolve_trend(
        self,
        feature_trend: TrendRegime,
        indicator_trend: TrendRegime,
        warnings: list[dict[str, object]],
    ) -> tuple[TrendRegime, Decimal]:
        if feature_trend != TrendRegime.UNCLEAR and feature_trend == indicator_trend:
            return feature_trend, Decimal("1.00")
        if feature_trend != TrendRegime.UNCLEAR and indicator_trend == TrendRegime.UNCLEAR:
            warnings.append(
                {
                    "code": "indicator_trend_missing",
                    "message": "Feature trend was present but indicator trend alignment was unavailable.",
                }
            )
            return feature_trend, Decimal("0.70")
        if feature_trend == TrendRegime.UNCLEAR and indicator_trend != TrendRegime.UNCLEAR:
            warnings.append(
                {
                    "code": "feature_trend_missing",
                    "message": "Indicator trend was present but feature trend was unavailable.",
                }
            )
            return indicator_trend, Decimal("0.60")
        if feature_trend == TrendRegime.UNCLEAR and indicator_trend == TrendRegime.UNCLEAR:
            warnings.append(
                {
                    "code": "trend_inputs_missing",
                    "message": "Feature and indicator trend inputs were unavailable.",
                }
            )
            return TrendRegime.UNCLEAR, Decimal("0.25")
        warnings.append(
            {
                "code": "trend_input_conflict",
                "message": "Feature trend and indicator trend did not agree.",
                "featureTrend": feature_trend.value,
                "indicatorTrend": indicator_trend.value,
            }
        )
        return TrendRegime.MIXED, Decimal("0.40")

    def resolve_volatility(
        self,
        features: dict[str, Any],
        indicators: dict[str, Any],
        warnings: list[dict[str, object]],
    ) -> VolatilityRegime:
        volatility = read_mapping(features, "volatility")
        feature_state = read_text(volatility, "volatilityState")
        atr = read_mapping(indicators, "atr")
        atr_state = read_text(atr, "state")
        large_candle_count = read_int(volatility, "largeCandleCount")
        selected_state = feature_state if feature_state not in {"", "unknown"} else atr_state
        if selected_state in {"compressed", "normal", "expanding", "spike"}:
            if selected_state == "expanding" and large_candle_count >= 3:
                return VolatilityRegime.HIGH_VOLATILITY
            return VolatilityRegime(selected_state)
        if large_candle_count >= 3:
            return VolatilityRegime.HIGH_VOLATILITY
        warnings.append(
            {
                "code": "volatility_inputs_missing",
                "message": "Volatility state inputs were unavailable.",
            }
        )
        return VolatilityRegime.UNCLEAR

    def resolve_range(
        self,
        features: dict[str, Any],
        signal: Signal | None,
        pattern_candidates: list[PatternCandidate],
        warnings: list[dict[str, object]],
    ) -> RangeRegime:
        if self.has_fakeout_risk(pattern_candidates):
            return RangeRegime.FAKEOUT_RISK
        range_features = read_mapping(features, "range")
        range_state = read_text(range_features, "rangeState")
        if range_state == "inside_previous_range":
            return RangeRegime.INSIDE_RANGE
        if range_state == "above_previous_range":
            return RangeRegime.BREAKOUT
        if range_state == "below_previous_range":
            return RangeRegime.BREAKDOWN
        pattern_type = (signal.pattern_type or "").lower() if signal else ""
        if "retest" in pattern_type:
            return RangeRegime.RANGE_RETEST
        if "breakout" in pattern_type:
            return RangeRegime.BREAKOUT
        if "breakdown" in pattern_type:
            return RangeRegime.BREAKDOWN
        warnings.append(
            {
                "code": "range_inputs_missing",
                "message": "Range state inputs were unavailable.",
            }
        )
        return RangeRegime.UNCLEAR

    def resolve_data_quality(
        self,
        features: dict[str, Any],
        strong_threshold: Decimal,
        acceptable_threshold: Decimal,
        warnings: list[dict[str, object]],
    ) -> tuple[DataQualityLabel, Decimal]:
        data_quality = read_mapping(features, "dataQuality")
        quality_score = read_decimal(data_quality, "qualityScore")
        missing_candles = read_int(data_quality, "missingCandles")
        duplicate_candles = read_int(data_quality, "duplicateCandles")
        if quality_score is None:
            warnings.append(
                {
                    "code": "data_quality_missing",
                    "message": "Feature snapshot did not include candle data quality.",
                }
            )
            return DataQualityLabel.DEGRADED, Decimal("0.40")
        if missing_candles or duplicate_candles:
            warnings.append(
                {
                    "code": "candle_quality_warnings",
                    "message": "Candle data quality included missing or duplicate candles.",
                    "missingCandles": missing_candles,
                    "duplicateCandles": duplicate_candles,
                }
            )
        if quality_score >= strong_threshold:
            return DataQualityLabel.STRONG, quality_score
        if quality_score >= acceptable_threshold:
            return DataQualityLabel.ACCEPTABLE, quality_score
        if quality_score > Decimal("0"):
            return DataQualityLabel.DEGRADED, quality_score
        return DataQualityLabel.INSUFFICIENT, Decimal("0")

    def feature_completeness_score(
        self,
        features: dict[str, Any],
        indicators: dict[str, Any],
    ) -> Decimal:
        sections = [
            read_mapping(features, "trend"),
            read_mapping(features, "volatility"),
            read_mapping(features, "range"),
            read_mapping(features, "dataQuality"),
            read_mapping(indicators, "ema"),
            read_mapping(indicators, "atr"),
        ]
        present = sum(1 for section in sections if section)
        return Decimal(present) / Decimal(len(sections))

    def pattern_signal_agreement_score(
        self,
        range_regime: RangeRegime,
        signal: Signal | None,
        pattern_candidates: list[PatternCandidate],
    ) -> Decimal:
        selected = [candidate for candidate in pattern_candidates if candidate.is_selected]
        if self.has_fakeout_risk(pattern_candidates):
            return Decimal("0.65")
        if signal is None and not selected:
            return Decimal("0.50")
        if selected:
            selected_type = selected[0].pattern_type.lower()
            if range_regime == RangeRegime.BREAKOUT and "breakout" in selected_type:
                return Decimal("0.90")
            if range_regime == RangeRegime.BREAKDOWN and "breakdown" in selected_type:
                return Decimal("0.90")
            if range_regime == RangeRegime.RANGE_RETEST and "retest" in selected_type:
                return Decimal("0.90")
            return Decimal("0.70")
        if signal is not None and signal.pattern_type:
            return Decimal("0.65")
        return Decimal("0.50")

    def has_fakeout_risk(self, pattern_candidates: list[PatternCandidate]) -> bool:
        for candidate in pattern_candidates:
            pattern_type = candidate.pattern_type.lower()
            if "fakeout" in pattern_type and candidate.strength_score >= Decimal("0.6500"):
                return True
            risk_notes = candidate.risk_notes_json or []
            risk_codes = [
                str(note.get("code", "")).lower()
                for note in risk_notes
                if isinstance(note, dict)
            ]
            if any("fakeout" in code for code in risk_codes):
                return True
        return False

    def feature_inputs(self, features: dict[str, Any]) -> dict[str, Any]:
        return {
            "trend": read_mapping(features, "trend"),
            "volatility": read_mapping(features, "volatility"),
            "range": read_mapping(features, "range"),
            "dataQuality": read_mapping(features, "dataQuality"),
        }

    def indicator_inputs(self, indicators: dict[str, Any]) -> dict[str, Any]:
        return {
            "ema": read_mapping(indicators, "ema"),
            "atr": read_mapping(indicators, "atr"),
            "calculation": read_mapping(indicators, "calculation"),
        }

    def confidence_label(self, confidence_score: Decimal) -> RegimeConfidenceLabel:
        if confidence_score >= Decimal("0.90"):
            return RegimeConfidenceLabel.VERY_HIGH
        if confidence_score >= Decimal("0.75"):
            return RegimeConfidenceLabel.HIGH
        if confidence_score >= Decimal("0.50"):
            return RegimeConfidenceLabel.MEDIUM
        return RegimeConfidenceLabel.LOW

    def selected_pattern_candidate_id(
        self,
        pattern_candidates: list[PatternCandidate],
    ) -> str | None:
        for candidate in pattern_candidates:
            if candidate.is_selected:
                return str(candidate.id)
        return None

    def summary(
        self,
        trend_regime: TrendRegime,
        volatility_regime: VolatilityRegime,
        range_regime: RangeRegime,
        data_quality_label: DataQualityLabel,
        confidence_label: RegimeConfidenceLabel,
    ) -> str:
        return (
            "Market regime context is "
            f"{trend_regime.value}, {volatility_regime.value}, and {range_regime.value} "
            f"with {data_quality_label.value} data quality and {confidence_label.value} "
            "regime confidence."
        )


def read_mapping(source: dict[str, Any], key: str) -> dict[str, Any]:
    value = source.get(key)
    if isinstance(value, dict):
        return value
    return {}


def read_text(source: dict[str, Any], key: str) -> str:
    value = source.get(key)
    if value is None:
        return ""
    return str(value)


def read_int(source: dict[str, Any], key: str) -> int:
    value = source.get(key)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def read_decimal(source: dict[str, Any], key: str) -> Decimal | None:
    value = source.get(key)
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def clamp(value: Decimal) -> Decimal:
    if value < Decimal("0"):
        return Decimal("0")
    if value > Decimal("1"):
        return Decimal("1")
    return value
