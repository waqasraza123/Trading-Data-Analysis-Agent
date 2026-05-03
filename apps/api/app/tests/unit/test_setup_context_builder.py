from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.setup_context.builder import (
    ALLOWED_NEXT_OBSERVATIONS,
    assert_setup_context_safety,
    safe_text,
)
from app.modules.setup_context.models import SetupContext


def test_setup_context_safety_allows_backend_observations() -> None:
    setup_context = setup_context_row(
        next_observations=[
            {"observation": observation, "source": "setup_context_policy"}
            for observation in sorted(ALLOWED_NEXT_OBSERVATIONS)
        ]
    )

    assert_setup_context_safety(setup_context)


def test_setup_context_safety_blocks_direct_market_actions() -> None:
    setup_context = setup_context_row(
        next_observations=[{"observation": "buy", "source": "unsafe"}],
    )

    with pytest.raises(ValueError, match="blocked language|unsupported next observations"):
        assert_setup_context_safety(setup_context)


def test_safe_text_rewrites_advisory_market_terms() -> None:
    text = safe_text("Use stop loss and take profit after buy or sell wording.")

    assert "stop loss" not in text.lower()
    assert "take profit" not in text.lower()
    assert "buy" not in text.lower()
    assert "sell" not in text.lower()
    assert "invalidation context" in text
    assert "target context" in text


def setup_context_row(next_observations: list[dict[str, object]]) -> SetupContext:
    identity = uuid4()
    return SetupContext(
        workspace_id=identity,
        signal_id=uuid4(),
        analysis_run_id=uuid4(),
        symbol_id=uuid4(),
        timeframe="1m",
        context_version="v1",
        status="completed",
        directional_bias="bullish",
        setup_quality_label="acceptable_context",
        setup_quality_score=Decimal("0.6500"),
        invalidation_context_json=[],
        observation_zones_json=[],
        target_context_zones_json=[],
        wait_conditions_json=[],
        avoid_reasons_json=[],
        timeframe_agreement_json={"agreement": "aligned"},
        data_quality_warnings_json=[],
        risk_notes_json=[],
        next_observations_json=next_observations,
        summary="Setup context completed. Not a trade instruction.",
        metadata_json={"policy": {"notATradeInstruction": True}},
    )
