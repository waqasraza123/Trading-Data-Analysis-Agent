from dataclasses import dataclass


@dataclass(frozen=True)
class EngineVersionDefinition:
    engine_name: str
    version: str
    description: str
    config_json: dict[str, object]


CURRENT_ENGINE_VERSIONS: tuple[EngineVersionDefinition, ...] = (
    EngineVersionDefinition(
        engine_name="feature_engine",
        version="v1",
        description="Deterministic movement, candle-shape, range, volatility, and trend features.",
        config_json={"artifact": "feature_snapshots", "status": "current"},
    ),
    EngineVersionDefinition(
        engine_name="indicator_engine",
        version="v1",
        description="Deterministic EMA, RSI, MACD, and ATR indicator snapshot engine.",
        config_json={"artifact": "indicator_snapshots", "status": "current"},
    ),
    EngineVersionDefinition(
        engine_name="pattern_engine",
        version="v1",
        description=(
            "Deterministic breakout, breakdown, continuation, reversal, fakeout, "
            "and chop detectors."
        ),
        config_json={"artifact": "pattern_candidates", "status": "current"},
    ),
    EngineVersionDefinition(
        engine_name="signal_classifier",
        version="v1",
        description="Deterministic strategy-profile signal classifier.",
        config_json={"artifact": "signals", "status": "current"},
    ),
    EngineVersionDefinition(
        engine_name="deterministic_explanation_engine",
        version="v1",
        description="Safe deterministic explanation template engine.",
        config_json={
            "artifact": "deterministic_explanations",
            "templateVersion": "deterministic_v1",
        },
    ),
    EngineVersionDefinition(
        engine_name="news_correlation_engine",
        version="v1",
        description="Deterministic event relevance and signal/news correlation scoring engine.",
        config_json={
            "artifact": "signal_news_correlations",
            "scorerVersion": "news_correlation_v1",
        },
    ),
    EngineVersionDefinition(
        engine_name="replay_engine",
        version="v1",
        description="Version-aware deterministic replay engine.",
        config_json={"artifact": "analysis_runs", "status": "current"},
    ),
)


CURRENT_ENGINE_VERSION_BY_NAME = {
    definition.engine_name: definition for definition in CURRENT_ENGINE_VERSIONS
}


def current_engine_snapshot() -> dict[str, object]:
    return {
        "engines": {
            definition.engine_name: {
                "version": definition.version,
                "description": definition.description,
                "config": definition.config_json,
            }
            for definition in CURRENT_ENGINE_VERSIONS
        }
    }


def is_supported_engine_snapshot(snapshot: dict[str, object] | None) -> bool:
    if snapshot is None:
        return True
    engines = snapshot.get("engines")
    if not isinstance(engines, dict):
        return False
    for engine_name, raw_engine in engines.items():
        if not isinstance(engine_name, str) or not isinstance(raw_engine, dict):
            return False
        version = raw_engine.get("version")
        definition = CURRENT_ENGINE_VERSION_BY_NAME.get(engine_name)
        if definition is None or definition.version != version:
            return False
    return True
