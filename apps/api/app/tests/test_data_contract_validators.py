from app.modules.data_contracts.models import DataContractValidationStatus
from app.modules.data_contracts.registry import DEFAULT_DATA_CONTRACT_BY_KEY_VERSION
from app.modules.data_contracts.validators import validate_payload_against_schema


def test_validate_payload_passes_with_warning_in_loose_mode() -> None:
    contract = DEFAULT_DATA_CONTRACT_BY_KEY_VERSION[("reasoning_output", "v1")]

    result = validate_payload_against_schema(
        {
            "summary": "Grounded summary",
            "scenarios": [],
            "extraField": "kept for compatibility",
        },
        contract.schema_json,
        strict=False,
    )

    assert result.status == DataContractValidationStatus.PASSED_WITH_WARNINGS
    assert result.errors == []
    assert result.warnings[0]["code"] == "unknown_field"


def test_validate_payload_fails_unknown_field_in_strict_mode() -> None:
    contract = DEFAULT_DATA_CONTRACT_BY_KEY_VERSION[("reasoning_output", "v1")]

    result = validate_payload_against_schema(
        {
            "summary": "Grounded summary",
            "scenarios": [],
            "extraField": "rejected in strict mode",
        },
        contract.schema_json,
        strict=True,
    )

    assert result.status == DataContractValidationStatus.FAILED
    assert result.errors[0]["code"] == "unknown_field"


def test_validate_payload_fails_missing_required_field() -> None:
    contract = DEFAULT_DATA_CONTRACT_BY_KEY_VERSION[("normalized_candle", "v1")]

    result = validate_payload_against_schema(
        {
            "workspaceId": "workspace",
            "symbolId": "symbol",
            "sourceId": "source",
            "timeframe": "1m",
            "timestamp": "2026-05-02T00:00:00Z",
            "open": "1.0",
            "high": "1.1",
            "low": "0.9",
            "isFinal": True,
            "originType": "json_import",
        },
        contract.schema_json,
        strict=False,
    )

    assert result.status == DataContractValidationStatus.FAILED
    assert result.errors[0]["code"] == "missing_required_field"
