from dataclasses import dataclass


@dataclass(frozen=True)
class DataContractDefinition:
    key: str
    version: str
    description: str
    schema_json: dict[str, object]
    metadata_json: dict[str, object]


def object_schema(
    properties: dict[str, object],
    required: list[str] | None = None,
    additional_properties: bool = True,
) -> dict[str, object]:
    return {
        "type": "object",
        "required": required or [],
        "properties": properties,
        "additionalProperties": additional_properties,
    }


def array_schema(items: dict[str, object]) -> dict[str, object]:
    return {"type": "array", "items": items}


def primitive_schema(type_name: str, enum: list[str] | None = None) -> dict[str, object]:
    schema: dict[str, object] = {"type": type_name}
    if enum is not None:
        schema["enum"] = enum
    return schema


STRING = primitive_schema("string")
NUMBER = primitive_schema("number")
INTEGER = primitive_schema("integer")
BOOLEAN = primitive_schema("boolean")
OBJECT = primitive_schema("object")


DEFAULT_DATA_CONTRACTS: tuple[DataContractDefinition, ...] = (
    DataContractDefinition(
        key="candle_import_row",
        version="v1",
        description="Raw imported OHLC candle row before shared normalization.",
        schema_json=object_schema(
            {
                "timestamp": STRING,
                "open": primitive_schema("market_number"),
                "high": primitive_schema("market_number"),
                "low": primitive_schema("market_number"),
                "close": primitive_schema("market_number"),
                "volume": primitive_schema("market_number"),
            },
            ["timestamp", "open", "high", "low", "close"],
        ),
        metadata_json={"artifact": "imports", "jsonbField": "import_errors.raw_row_json"},
    ),
    DataContractDefinition(
        key="normalized_candle",
        version="v1",
        description=(
            "Shared normalized candle payload used by imports, polling, live feeds, "
            "and screenshots."
        ),
        schema_json=object_schema(
            {
                "workspaceId": STRING,
                "symbolId": STRING,
                "sourceId": STRING,
                "timeframe": STRING,
                "timestamp": STRING,
                "open": primitive_schema("market_number"),
                "high": primitive_schema("market_number"),
                "low": primitive_schema("market_number"),
                "close": primitive_schema("market_number"),
                "volume": primitive_schema("market_number"),
                "isFinal": BOOLEAN,
                "originType": STRING,
                "originReferenceId": STRING,
            },
            [
                "workspaceId",
                "symbolId",
                "sourceId",
                "timeframe",
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "isFinal",
                "originType",
            ],
        ),
        metadata_json={
            "artifact": "candles",
            "sourceTypes": [
                "csv_import",
                "json_import",
                "live_feed",
                "api_polling",
                "chart_screenshot",
            ],
        },
    ),
    DataContractDefinition(
        key="feature_snapshot",
        version="v1",
        description="Deterministic feature snapshot JSONB artifact for an analysis run.",
        schema_json=object_schema(
            {
                "movement": OBJECT,
                "candleShape": OBJECT,
                "range": OBJECT,
                "volatility": OBJECT,
                "trend": OBJECT,
            },
            [],
        ),
        metadata_json={"artifact": "feature_snapshots", "jsonbField": "features_json"},
    ),
    DataContractDefinition(
        key="indicator_snapshot",
        version="v1",
        description="Deterministic indicator snapshot JSONB artifact.",
        schema_json=object_schema(
            {
                "ema": OBJECT,
                "rsi": OBJECT,
                "macd": OBJECT,
                "atr": OBJECT,
                "isReady": BOOLEAN,
            },
            [],
        ),
        metadata_json={"artifact": "indicator_snapshots", "jsonbField": "indicators_json"},
    ),
    DataContractDefinition(
        key="strategy_profile_config",
        version="v1",
        description="Deterministic strategy profile configuration payload.",
        schema_json=object_schema(
            {
                "key": STRING,
                "version": STRING,
                "allowedPatterns": array_schema(STRING),
                "excludedPatterns": array_schema(STRING),
                "minimumCandidateStrength": primitive_schema("market_number"),
                "minimumConfidence": primitive_schema("market_number"),
                "componentWeights": OBJECT,
                "riskFilters": OBJECT,
                "noSignalRules": OBJECT,
            },
            ["key", "version", "componentWeights", "riskFilters", "noSignalRules"],
        ),
        metadata_json={
            "artifact": "strategy_profiles",
            "jsonbFields": [
                "component_weights_json",
                "risk_filters_json",
                "no_signal_rules_json",
            ],
        },
    ),
    DataContractDefinition(
        key="signal_snapshot",
        version="v1",
        description="Persisted deterministic signal and strategy snapshot payload.",
        schema_json=object_schema(
            {
                "signalId": STRING,
                "analysisRunId": STRING,
                "bias": STRING,
                "classificationStatus": STRING,
                "confidenceScore": primitive_schema("market_number"),
                "confidenceLabel": STRING,
                "strategyProfile": OBJECT,
                "summary": STRING,
            },
            ["bias", "classificationStatus", "confidenceScore", "confidenceLabel", "summary"],
        ),
        metadata_json={"artifact": "signals", "jsonbField": "strategy_profile_snapshot_json"},
    ),
    DataContractDefinition(
        key="outcome_metadata",
        version="v1",
        description="Signal outcome metadata JSONB artifact.",
        schema_json=object_schema(
            {
                "evaluationVersion": STRING,
                "horizonMinutes": INTEGER,
                "notes": array_schema(STRING),
                "source": STRING,
            },
            [],
        ),
        metadata_json={"artifact": "signal_outcomes", "jsonbField": "metadata_json"},
    ),
    DataContractDefinition(
        key="reasoning_output",
        version="v1",
        description="Grounded scenario reasoning output JSONB artifact.",
        schema_json=object_schema(
            {
                "summary": STRING,
                "scenarios": array_schema(OBJECT),
                "limitations": array_schema(STRING),
                "fallbackUsed": BOOLEAN,
                "errorMessage": STRING,
            },
            ["summary", "scenarios"],
        ),
        metadata_json={"artifact": "llm_reasoning_runs", "jsonbField": "output_json"},
    ),
    DataContractDefinition(
        key="scenario_hypothesis",
        version="v1",
        description="Persisted scenario hypothesis JSON-compatible artifact.",
        schema_json=object_schema(
            {
                "scenarioType": STRING,
                "scenarioLabel": STRING,
                "possibilityLabel": STRING,
                "supportingEvidence": array_schema(STRING),
                "conflictingEvidence": array_schema(STRING),
                "outcomeHistory": OBJECT,
                "nextObservations": array_schema(STRING),
                "suggestedBackendActions": array_schema(STRING),
                "riskNotes": array_schema(STRING),
            },
            ["scenarioType", "scenarioLabel", "possibilityLabel"],
        ),
        metadata_json={"artifact": "scenario_hypotheses"},
    ),
    DataContractDefinition(
        key="webhook_payload",
        version="v1",
        description="Inbound provider or webhook payload captured before deterministic processing.",
        schema_json=object_schema(
            {
                "provider": STRING,
                "eventType": STRING,
                "receivedAt": STRING,
                "payload": OBJECT,
            },
            [],
        ),
        metadata_json={"artifact": "live_feed_events", "jsonbField": "payload_json"},
    ),
    DataContractDefinition(
        key="dataset_record",
        version="v1",
        description="Generic dataset record payload reserved for future dataset storage.",
        schema_json=object_schema(
            {
                "recordId": STRING,
                "workspaceId": STRING,
                "recordType": STRING,
                "payload": OBJECT,
                "labels": OBJECT,
                "metadata": OBJECT,
            },
            ["payload"],
        ),
        metadata_json={"artifact": "datasets", "status": "registered_for_future_storage"},
    ),
    DataContractDefinition(
        key="chart_axis_calibration",
        version="v1",
        description=(
            "Chart screenshot axis calibration metadata extracted from OCR or manual calibration."
        ),
        schema_json=object_schema(
            {
                "priceAxis": OBJECT,
                "timeAxis": OBJECT,
                "confidence": primitive_schema("market_number"),
                "source": STRING,
                "warnings": array_schema(STRING),
            },
            [],
        ),
        metadata_json={
            "artifact": "chart_screenshot_runs",
            "jsonbPath": "parser_metadata_json.axisCalibration",
        },
    ),
    DataContractDefinition(
        key="chart_ocr_metadata",
        version="v1",
        description=(
            "Chart screenshot OCR metadata used for extraction confidence and review gating."
        ),
        schema_json=object_schema(
            {
                "status": STRING,
                "provider": STRING,
                "confidence": primitive_schema("market_number"),
                "text": STRING,
                "warnings": array_schema(STRING),
            },
            [],
        ),
        metadata_json={
            "artifact": "chart_screenshot_runs",
            "jsonbPath": "parser_metadata_json.ocr",
        },
    ),
)


DEFAULT_DATA_CONTRACT_BY_KEY_VERSION = {
    (definition.key, definition.version): definition for definition in DEFAULT_DATA_CONTRACTS
}
