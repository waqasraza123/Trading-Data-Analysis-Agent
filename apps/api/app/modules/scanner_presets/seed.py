from app.modules.scanner_presets.models import (
    ScannerPreset,
    ScannerPresetCategory,
    ScannerPresetStatus,
)


def default_scanner_presets(preset_version: str) -> tuple[ScannerPreset, ...]:
    return (
        build_preset(
            preset_version,
            key="london_open",
            name="London open",
            description=(
                "Creates a focused London-session watchlist and scheduled scan config for "
                "stored FX and metals candles."
            ),
            category=ScannerPresetCategory.SESSION,
            market_types=["forex", "commodity"],
            symbols=["EURUSD", "GBPUSD", "XAUUSD"],
            timeframes=["5m", "15m"],
            session_labels=["london", "overlap"],
            lookback_minutes=240,
            interval_seconds=900,
            metadata={"reviewContext": "london_open", "safeUse": "session_review"},
        ),
        build_preset(
            preset_version,
            key="new_york_open",
            name="New York open",
            description=(
                "Creates a New York-session review watchlist and scheduled scan config for "
                "stored major-market candles."
            ),
            category=ScannerPresetCategory.SESSION,
            market_types=["forex", "commodity"],
            symbols=["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"],
            timeframes=["5m", "15m"],
            session_labels=["new_york", "overlap"],
            lookback_minutes=240,
            interval_seconds=900,
            metadata={"reviewContext": "new_york_open", "safeUse": "session_review"},
        ),
        build_preset(
            preset_version,
            key="crypto_24h",
            name="Crypto 24h",
            description=(
                "Creates a continuous crypto watchlist and scheduled scan config for stored "
                "24-hour market data review."
            ),
            category=ScannerPresetCategory.MARKET,
            market_types=["crypto"],
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframes=["15m", "1h"],
            session_labels=["asia", "london", "new_york", "overlap", "off_hours"],
            lookback_minutes=720,
            interval_seconds=1800,
            metadata={"reviewContext": "crypto_24h", "safeUse": "continuous_market_review"},
        ),
        build_preset(
            preset_version,
            key="high_volatility",
            name="High volatility",
            description=(
                "Creates a watchlist and scheduled scan config for reviewing expanded volatility "
                "contexts in stored candles."
            ),
            category=ScannerPresetCategory.VOLATILITY,
            market_types=["forex", "crypto", "commodity"],
            symbols=["BTCUSDT", "ETHUSDT", "XAUUSD", "GBPUSD"],
            timeframes=["1m", "5m", "15m"],
            session_labels=["london", "new_york", "overlap"],
            lookback_minutes=180,
            interval_seconds=600,
            metadata={"reviewContext": "high_volatility", "safeUse": "volatility_review"},
        ),
        build_preset(
            preset_version,
            key="trend_continuation",
            name="Trend continuation",
            description=(
                "Creates a review watchlist and scheduled scan config for stored multi-timeframe "
                "continuation context."
            ),
            category=ScannerPresetCategory.PATTERN_CONTEXT,
            market_types=["forex", "crypto", "commodity"],
            symbols=["EURUSD", "BTCUSDT", "ETHUSDT", "XAUUSD"],
            timeframes=["15m", "1h", "4h"],
            session_labels=["london", "new_york", "overlap"],
            lookback_minutes=960,
            interval_seconds=1800,
            pattern_filters=["continuation", "bullish_breakout", "bearish_breakdown"],
            metadata={"reviewContext": "trend_continuation", "safeUse": "context_review"},
        ),
        build_preset(
            preset_version,
            key="reversal_risk",
            name="Reversal risk",
            description=(
                "Creates a watchlist and scheduled scan config for reviewing stored reversal and "
                "rejection contexts."
            ),
            category=ScannerPresetCategory.PATTERN_CONTEXT,
            market_types=["forex", "crypto", "commodity"],
            symbols=["EURUSD", "GBPUSD", "BTCUSDT", "XAUUSD"],
            timeframes=["5m", "15m", "1h"],
            session_labels=["london", "new_york", "overlap"],
            lookback_minutes=480,
            interval_seconds=1200,
            pattern_filters=["reversal", "fakeout"],
            metadata={"reviewContext": "reversal_risk", "safeUse": "risk_context_review"},
        ),
        build_preset(
            preset_version,
            key="range_no_directional",
            name="Range / no directional signal",
            description=(
                "Creates a review watchlist and scheduled scan config for range, chop, and "
                "no-directional contexts."
            ),
            category=ScannerPresetCategory.PATTERN_CONTEXT,
            market_types=["forex", "crypto", "commodity"],
            symbols=["EURUSD", "USDJPY", "BTCUSDT", "XAUUSD"],
            timeframes=["15m", "1h"],
            session_labels=["asia", "london", "new_york", "off_hours"],
            lookback_minutes=720,
            interval_seconds=1800,
            pattern_filters=["chop", "range", "no_directional_signal"],
            metadata={"reviewContext": "range_no_directional", "safeUse": "avoid_context_review"},
        ),
        build_preset(
            preset_version,
            key="needs_confirmation",
            name="Needs confirmation",
            description=(
                "Creates a watchlist and scheduled scan config for contexts that require fresher "
                "data or timeframe agreement review."
            ),
            category=ScannerPresetCategory.PATTERN_CONTEXT,
            market_types=["forex", "crypto", "commodity"],
            symbols=["EURUSD", "GBPUSD", "BTCUSDT", "ETHUSDT", "XAUUSD"],
            timeframes=["5m", "15m", "1h"],
            session_labels=["london", "new_york", "overlap"],
            lookback_minutes=360,
            interval_seconds=900,
            preference_filters={
                "requireFreshData": True,
                "requireTimeframeAgreement": True,
                "requireAcceptableDataQuality": True,
            },
            metadata={"reviewContext": "needs_confirmation", "safeUse": "confirmation_review"},
        ),
        build_preset(
            preset_version,
            key="stale_data_repair",
            name="Stale data repair",
            description=(
                "Creates a watchlist and scheduled scan config for reviewing symbols that need "
                "freshness or data-quality repair."
            ),
            category=ScannerPresetCategory.DATA_REPAIR,
            market_types=["forex", "crypto", "commodity"],
            symbols=["EURUSD", "GBPUSD", "USDJPY", "BTCUSDT", "ETHUSDT", "XAUUSD"],
            timeframes=["1m", "5m", "15m", "1h"],
            session_labels=["asia", "london", "new_york", "overlap", "off_hours"],
            lookback_minutes=120,
            interval_seconds=3600,
            preference_filters={"requireFreshData": True, "requireAcceptableDataQuality": True},
            metadata={"reviewContext": "stale_data_repair", "safeUse": "data_repair_review"},
        ),
        build_preset(
            preset_version,
            key="close_of_day_review",
            name="Close-of-day review",
            description=(
                "Creates a watchlist and scheduled scan config for stored higher-timeframe "
                "end-of-day review."
            ),
            category=ScannerPresetCategory.REVIEW,
            market_types=["forex", "crypto", "commodity"],
            symbols=["EURUSD", "GBPUSD", "USDJPY", "BTCUSDT", "ETHUSDT", "XAUUSD"],
            timeframes=["1h", "4h", "1d"],
            session_labels=["new_york", "off_hours"],
            lookback_minutes=1440,
            interval_seconds=86400,
            metadata={"reviewContext": "close_of_day_review", "safeUse": "end_of_day_review"},
        ),
    )


def build_preset(
    preset_version: str,
    *,
    key: str,
    name: str,
    description: str,
    category: ScannerPresetCategory,
    market_types: list[str],
    symbols: list[str],
    timeframes: list[str],
    session_labels: list[str],
    lookback_minutes: int,
    interval_seconds: int,
    pattern_filters: list[str] | None = None,
    preference_filters: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> ScannerPreset:
    return ScannerPreset(
        workspace_id=None,
        key=key,
        name=name,
        description=description,
        category=category.value,
        status=ScannerPresetStatus.ACTIVE.value,
        preset_version=preset_version,
        market_types_json=market_types,
        symbol_templates_json=[{"symbols": symbols}],
        timeframe_templates_json=timeframes,
        session_filters_json={"sessionLabels": session_labels},
        scan_config_template_json={
            "scanMode": "watchlist",
            "lookbackMinutes": lookback_minutes,
            "intervalSeconds": interval_seconds,
            "includePartialLiveCandle": False,
            "includeNewsCorrelation": False,
            "includeAiExplanation": False,
            "includeReasoning": False,
            "includeActionPlan": False,
        },
        watchlist_template_json={
            "includePartialLiveCandle": False,
            "itemMetadata": {"presetKey": key, "presetVersion": preset_version},
        },
        preference_profile_filters_json={
            "sessionLabels": session_labels,
            "marketTypes": market_types,
            "patternTypes": pattern_filters or [],
            **(preference_filters or {}),
        },
        metadata_json={
            "doesNotRunScans": True,
            "doesNotCreateSetups": True,
            "createdArtifacts": ["watchlist", "scheduled_scan_config"],
            **(metadata or {}),
        },
    )
