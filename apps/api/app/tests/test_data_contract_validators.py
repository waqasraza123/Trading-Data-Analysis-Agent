from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.modules.data_contracts.models import DataContractValidationStatus
from app.modules.data_contracts.registry import DEFAULT_DATA_CONTRACT_BY_KEY_VERSION
from app.modules.data_contracts.schemas import DataContractRead
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


def test_data_contract_read_serializes_schema_json_alias() -> None:
    contract_id = uuid4()
    now = datetime(2026, 5, 10, tzinfo=UTC)
    contract = SimpleNamespace(
        id=contract_id,
        key="normalized_candle",
        version="v1",
        status="active",
        description="Normalized candle contract",
        schema_json={"type": "object", "required": ["open"]},
        metadata_json={"owner": "tests"},
        created_at=now,
        updated_at=now,
    )

    result = DataContractRead.model_validate(contract)
    payload = result.model_dump(by_alias=True)

    assert result.schema_definition == {"type": "object", "required": ["open"]}
    assert payload["schema_json"] == {"type": "object", "required": ["open"]}
    assert "schema_definition" not in payload
