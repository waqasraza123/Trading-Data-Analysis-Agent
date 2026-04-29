from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class StrategyProfileDefinition:
    key: str
    name: str
    description: str
    version: str
    allowed_patterns: tuple[str, ...]
    excluded_patterns: tuple[str, ...]
    minimum_candidate_strength: Decimal
    minimum_confidence: Decimal
    component_weights: dict[str, str]
    risk_filters: dict[str, object]
    no_signal_rules: dict[str, object]


DEFAULT_STRATEGY_PROFILES: tuple[StrategyProfileDefinition, ...] = (
    StrategyProfileDefinition(
        key="breakout_continuation",
        name="Breakout Continuation",
        description=(
            "Classifies clean breakout and continuation setups when structure, "
            "volatility, and candidate strength are aligned."
        ),
        version="v1",
        allowed_patterns=(
            "bullish_breakout",
            "bearish_breakdown",
            "bullish_continuation",
            "bearish_continuation",
        ),
        excluded_patterns=(
            "fakeout",
            "sideways_range",
            "low_volatility_chop",
            "unclear_structure",
        ),
        minimum_candidate_strength=Decimal("0.6500"),
        minimum_confidence=Decimal("0.6500"),
        component_weights={
            "pattern_strength": "0.35",
            "trend_alignment": "0.20",
            "volatility_confirmation": "0.20",
            "indicator_support": "0.15",
            "data_quality": "0.10",
        },
        risk_filters={
            "minimum_data_quality": "0.9000",
            "fakeout_override_margin": "0.1200",
            "chop_override_margin": "0.1000",
            "opposing_bias_conflict_margin": "0.0800",
            "compressed_volatility_blocks_directional": True,
            "contradicting_trend_blocks_directional": True,
        },
        no_signal_rules={
            "low_data_quality": True,
            "fakeout_risk": True,
            "compressed_volatility": True,
            "contradicting_trend": True,
        },
    ),
    StrategyProfileDefinition(
        key="reversal_rejection",
        name="Reversal Rejection",
        description=(
            "Classifies reversal and rejection behavior when price rejects a boundary "
            "or prior movement weakens."
        ),
        version="v1",
        allowed_patterns=("bullish_reversal", "bearish_reversal"),
        excluded_patterns=(),
        minimum_candidate_strength=Decimal("0.6200"),
        minimum_confidence=Decimal("0.6000"),
        component_weights={
            "pattern_strength": "0.40",
            "trend_alignment": "0.15",
            "volatility_confirmation": "0.15",
            "indicator_support": "0.15",
            "data_quality": "0.15",
        },
        risk_filters={
            "minimum_data_quality": "0.8500",
            "reversal_required_margin": "0.0800",
            "chop_override_margin": "0.1000",
            "opposing_bias_conflict_margin": "0.0800",
        },
        no_signal_rules={
            "weak_reversal_evidence": True,
            "missing_follow_through": True,
            "low_data_quality": True,
            "chop_override": True,
            "stronger_opposing_continuation": True,
        },
    ),
    StrategyProfileDefinition(
        key="range_chop_avoidance",
        name="Range Chop Avoidance",
        description=(
            "Protects classification from forcing directional signals in unclear, "
            "sideways, low-volatility, or choppy markets."
        ),
        version="v1",
        allowed_patterns=("sideways_range", "low_volatility_chop", "unclear_structure"),
        excluded_patterns=(),
        minimum_candidate_strength=Decimal("0.5000"),
        minimum_confidence=Decimal("0.5000"),
        component_weights={
            "pattern_strength": "0.45",
            "trend_alignment": "0.10",
            "volatility_confirmation": "0.20",
            "indicator_support": "0.05",
            "data_quality": "0.20",
        },
        risk_filters={
            "minimum_data_quality": "0.7500",
            "chop_override_margin": "0.1000",
            "opposing_bias_conflict_margin": "0.0800",
        },
        no_signal_rules={
            "low_movement_efficiency": True,
            "frequent_direction_changes": True,
            "sideways_or_unclear_trend": True,
            "compressed_volatility": True,
            "directional_candidates_below_threshold": True,
        },
    ),
    StrategyProfileDefinition(
        key="fakeout_protection",
        name="Fakeout Protection",
        description=(
            "Prevents false breakout classification when fakeout evidence is stronger "
            "than breakout or continuation evidence."
        ),
        version="v1",
        allowed_patterns=("fakeout",),
        excluded_patterns=(),
        minimum_candidate_strength=Decimal("0.5800"),
        minimum_confidence=Decimal("0.5800"),
        component_weights={
            "pattern_strength": "0.45",
            "trend_alignment": "0.10",
            "volatility_confirmation": "0.15",
            "indicator_support": "0.05",
            "data_quality": "0.25",
        },
        risk_filters={
            "minimum_data_quality": "0.7500",
            "fakeout_override_margin": "0.1200",
            "opposing_bias_conflict_margin": "0.0800",
        },
        no_signal_rules={
            "fakeout_within_conflict_margin": True,
            "failed_to_hold_outside_range": True,
            "wick_rejection": True,
            "contradicting_follow_through": True,
        },
    ),
)
