from decimal import Decimal

from app.modules.profile_governance.diff import diff_profile_config
from app.modules.profile_governance.validator import validate_profile_config


def valid_profile_config() -> dict[str, object]:
    return {
        "allowed_patterns_json": ["bullish_breakout", "bearish_breakdown"],
        "excluded_patterns_json": ["fakeout"],
        "minimum_candidate_strength": "0.6500",
        "minimum_confidence": "0.6500",
        "component_weights_json": {
            "pattern_strength": "0.35",
            "trend_alignment": "0.20",
            "volatility_confirmation": "0.20",
            "indicator_support": "0.15",
            "data_quality": "0.10",
        },
        "risk_filters_json": {"minimum_data_quality": "0.9000"},
        "no_signal_rules_json": {"fakeout_risk": True},
    }


def test_profile_governance_validator_accepts_safe_market_reading_config() -> None:
    result = validate_profile_config(
        draft_key="breakout_continuation",
        draft_version="v2",
        config=valid_profile_config(),
    )

    assert result.status == "valid"
    assert result.errors == []


def test_profile_governance_validator_rejects_execution_fields() -> None:
    config = valid_profile_config()
    config["risk_filters_json"] = {"broker": "paper", "minimum_data_quality": "0.9000"}

    result = validate_profile_config(
        draft_key="breakout_continuation",
        draft_version="v2",
        config=config,
    )

    assert result.status == "invalid"
    assert any(error.code == "execution_key_not_allowed" for error in result.errors)


def test_profile_governance_validator_warns_when_weights_do_not_sum_close_to_one() -> None:
    config = valid_profile_config()
    config["component_weights_json"] = {
        "pattern_strength": "0.35",
        "trend_alignment": "0.20",
        "volatility_confirmation": "0.20",
    }

    result = validate_profile_config(
        draft_key="breakout_continuation",
        draft_version="v2",
        config=config,
    )

    assert result.status == "valid_with_warnings"
    assert any(error.code == "weights_sum_not_close_to_one" for error in result.warnings)


def test_profile_governance_validator_rejects_unsupported_pattern_types() -> None:
    config = valid_profile_config()
    config["allowed_patterns_json"] = ["unregistered_pattern"]

    result = validate_profile_config(
        draft_key="breakout_continuation",
        draft_version="v2",
        config=config,
    )

    assert result.status == "invalid"
    assert any(error.code == "unsupported_pattern_type" for error in result.errors)


def test_profile_governance_diff_tracks_pattern_threshold_and_weight_changes() -> None:
    base = valid_profile_config()
    proposed = valid_profile_config()
    proposed["allowed_patterns_json"] = ["bullish_breakout", "bullish_continuation"]
    proposed["minimum_confidence"] = Decimal("0.7000")
    proposed["component_weights_json"] = {
        "pattern_strength": "0.40",
        "trend_alignment": "0.20",
        "volatility_confirmation": "0.15",
        "indicator_support": "0.15",
        "data_quality": "0.10",
    }

    result = diff_profile_config(base, proposed)

    assert result["allowedPatterns"] == {
        "added": ["bullish_continuation"],
        "removed": ["bearish_breakdown"],
    }
    assert result["minimumThresholds"] == {
        "minimum_confidence": {"from": "0.6500", "to": "0.7000"}
    }
    assert result["componentWeights"]["changed"]["pattern_strength"] == {
        "from": "0.35",
        "to": "0.40",
    }
