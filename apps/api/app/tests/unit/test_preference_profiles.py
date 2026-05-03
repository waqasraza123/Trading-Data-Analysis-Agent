from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.market_sessions.models import MarketSessionContext
from app.modules.preference_profiles.matcher import (
    PreferenceProfileMatcher,
    PreferenceSignalContext,
)
from app.modules.preference_profiles.models import (
    PersonalStrategyPreferenceProfile,
    PreferenceProfileStatus,
)
from app.modules.preference_profiles.schemas import PreferenceProfileCreate
from app.modules.setup_context.models import SetupContext
from app.modules.signals.models import Signal
from app.modules.symbols.models import MarketType, Symbol


def test_preference_profile_create_normalizes_lists_and_name() -> None:
    payload = PreferenceProfileCreate(
        workspace_id=uuid4(),
        name="  London review  ",
        market_types_json=[MarketType.FOREX, MarketType.FOREX],
        pattern_types_json=[" bullish_breakout ", "bullish_breakout", ""],
        strategy_profile_keys_json=["breakout_continuation", "breakout_continuation"],
    )

    assert payload.name == "London review"
    assert payload.market_types_json == [MarketType.FOREX]
    assert payload.pattern_types_json == ["bullish_breakout"]
    assert payload.strategy_profile_keys_json == ["breakout_continuation"]


def test_preference_profile_create_rejects_blank_name() -> None:
    with pytest.raises(ValueError, match="name must not be blank"):
        PreferenceProfileCreate(workspace_id=uuid4(), name="   ")


def test_matcher_returns_match_with_included_reasons() -> None:
    workspace_id = uuid4()
    symbol_id = uuid4()
    signal = signal_fixture(workspace_id=workspace_id, symbol_id=symbol_id)
    profile = profile_fixture(
        workspace_id=workspace_id,
        symbol_ids_json=[str(symbol_id)],
        market_types_json=["forex"],
        timeframes_json=["5m"],
        session_labels_json=["london"],
        pattern_types_json=["bullish_breakout"],
        strategy_profile_keys_json=["breakout_continuation"],
        minimum_confidence=Decimal("0.7000"),
        minimum_setup_quality=Decimal("0.6000"),
        max_stale_seconds=600,
        require_fresh_data=True,
        require_timeframe_agreement=True,
        require_acceptable_data_quality=True,
    )

    result = PreferenceProfileMatcher().match(
        profile,
        PreferenceSignalContext(
            signal=signal,
            symbol=symbol_fixture(symbol_id),
            setup_context=setup_context_fixture(signal),
            market_session=market_session_fixture(signal),
            market_memory=market_memory_fixture(signal, fresh=True),
            evaluated_at=signal.created_at + timedelta(seconds=120),
        ),
    )

    assert result.matches is True
    assert result.excluded_reasons == []
    assert "Signal symbol is in the preferred symbol list." in result.included_reasons


def test_matcher_excludes_avoided_pattern_without_mutating_signal() -> None:
    signal = signal_fixture()
    original_pattern = signal.pattern_type
    profile = profile_fixture(
        workspace_id=signal.workspace_id,
        excluded_pattern_types_json=["bullish_breakout"],
    )

    result = PreferenceProfileMatcher().match(profile, PreferenceSignalContext(signal=signal))

    assert result.matches is False
    assert "Signal pattern is in the avoid pattern list." in result.excluded_reasons
    assert signal.pattern_type == original_pattern


def test_matcher_warns_on_missing_optional_market_context() -> None:
    signal = signal_fixture()
    profile = profile_fixture(
        workspace_id=signal.workspace_id,
        market_types_json=["forex"],
        include_news_context=True,
        include_outcomes=True,
    )

    result = PreferenceProfileMatcher().match(profile, PreferenceSignalContext(signal=signal))

    assert result.matches is True
    assert "Symbol market type was unavailable." in result.preference_warnings
    assert "News context is preferred when available." in result.preference_warnings
    assert "Outcome context is preferred when available." in result.preference_warnings


def profile_fixture(
    workspace_id: UUID,
    **overrides: object,
) -> PersonalStrategyPreferenceProfile:
    values = {
        "id": uuid4(),
        "workspace_id": workspace_id,
        "user_id": None,
        "name": "Preference profile",
        "description": None,
        "status": PreferenceProfileStatus.ACTIVE.value,
        "is_default": False,
        "market_types_json": [],
        "symbol_ids_json": [],
        "excluded_symbol_ids_json": [],
        "timeframes_json": [],
        "session_labels_json": [],
        "pattern_types_json": [],
        "excluded_pattern_types_json": [],
        "strategy_profile_keys_json": [],
        "minimum_confidence": None,
        "minimum_setup_quality": None,
        "max_stale_seconds": None,
        "require_fresh_data": False,
        "require_timeframe_agreement": False,
        "require_acceptable_data_quality": False,
        "include_news_context": False,
        "include_outcomes": False,
        "notification_preferences_json": {},
        "metadata_json": {},
        **overrides,
    }
    return PersonalStrategyPreferenceProfile(**values)


def signal_fixture(
    workspace_id: UUID | None = None,
    symbol_id: UUID | None = None,
) -> Signal:
    return Signal(
        id=uuid4(),
        workspace_id=workspace_id or uuid4(),
        symbol_id=symbol_id or uuid4(),
        analysis_run_id=uuid4(),
        timeframe="5m",
        strategy_profile_key="breakout_continuation",
        strategy_profile_id=None,
        strategy_profile_version="v1",
        strategy_profile_snapshot_json=None,
        bias="bullish",
        pattern_type="bullish_breakout",
        classification_status="signal",
        confidence_score=Decimal("0.8200"),
        confidence_label="high",
        candidate_strength=Decimal("0.7800"),
        selected_pattern_candidate_id=None,
        pips_moved=None,
        tick_moved=None,
        movement_direction=None,
        movement_quality=None,
        volatility_state=None,
        trend_state=None,
        range_state=None,
        summary="Deterministic context",
        no_signal_reason=None,
        created_at=datetime(2026, 5, 3, 12, 0, tzinfo=UTC),
    )


def symbol_fixture(symbol_id: UUID) -> Symbol:
    return Symbol(
        id=symbol_id,
        symbol="EURUSD",
        display_name="EUR/USD",
        market_type="forex",
        is_active=True,
    )


def setup_context_fixture(signal: Signal) -> SetupContext:
    return SetupContext(
        id=uuid4(),
        workspace_id=signal.workspace_id,
        signal_id=signal.id,
        analysis_run_id=signal.analysis_run_id,
        symbol_id=signal.symbol_id,
        timeframe=signal.timeframe,
        context_version="v1",
        status="completed",
        directional_bias="bullish",
        setup_quality_label="acceptable_context",
        setup_quality_score=Decimal("0.7600"),
        invalidation_context_json=[],
        observation_zones_json=[],
        target_context_zones_json=[],
        wait_conditions_json=[],
        avoid_reasons_json=[],
        timeframe_agreement_json={"isAligned": True},
        data_quality_warnings_json=[],
        risk_notes_json=[],
        next_observations_json=[],
        summary="Setup context",
        metadata_json={},
    )


def market_session_fixture(signal: Signal) -> MarketSessionContext:
    return MarketSessionContext(
        id=uuid4(),
        workspace_id=signal.workspace_id,
        analysis_run_id=signal.analysis_run_id,
        signal_id=signal.id,
        symbol_id=signal.symbol_id,
        timeframe=signal.timeframe,
        context_time=signal.created_at,
        timezone_name="UTC",
        session_version="v1",
        session_label="london",
        confidence_score=Decimal("0.9000"),
        context_json={},
    )


def market_memory_fixture(signal: Signal, fresh: bool) -> RollingMarketStateSnapshot:
    return RollingMarketStateSnapshot(
        id=uuid4(),
        workspace_id=signal.workspace_id,
        symbol_id=signal.symbol_id,
        source_id=None,
        timeframe=signal.timeframe,
        state_version="v1",
        latest_final_candle_time=signal.created_at,
        latest_analysis_run_id=signal.analysis_run_id,
        latest_signal_id=signal.id,
        latest_outcome_id=None,
        data_quality_label="acceptable",
        freshness_label="fresh" if fresh else "stale",
        trend_state=None,
        volatility_state=None,
        range_state=None,
        market_regime_label=None,
        market_session_label="london",
        multi_timeframe_label=None,
        cross_asset_label=None,
        latest_signal_bias="bullish",
        latest_signal_pattern_type=signal.pattern_type,
        latest_signal_confidence_label=signal.confidence_label,
        context_json={},
        warnings_json=[],
    )
