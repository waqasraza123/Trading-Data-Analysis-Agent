from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.data_contracts.models import DataContractValidationStatus


@dataclass(frozen=True)
class DataContractValidationOutcome:
    status: DataContractValidationStatus
    errors: list[dict[str, object]]
    warnings: list[dict[str, object]]
    payload_summary: dict[str, object]


def validate_payload_against_schema(
    payload: dict[str, Any] | list[Any],
    schema: dict[str, object],
    strict: bool,
) -> DataContractValidationOutcome:
    errors: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    validate_node(payload, schema, "$", strict, errors, warnings)
    summary = summarize_payload(payload)
    if errors:
        status = DataContractValidationStatus.FAILED
    elif warnings:
        status = DataContractValidationStatus.PASSED_WITH_WARNINGS
    else:
        status = DataContractValidationStatus.PASSED
    return DataContractValidationOutcome(
        status=status,
        errors=errors,
        warnings=warnings,
        payload_summary=summary,
    )


def validate_node(
    value: object,
    schema: dict[str, object],
    path: str,
    strict: bool,
    errors: list[dict[str, object]],
    warnings: list[dict[str, object]],
) -> None:
    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not value_matches_type(value, expected_type):
        errors.append(
            {
                "path": path,
                "code": "invalid_type",
                "message": f"Expected {expected_type}",
                "actualType": type(value).__name__,
            }
        )
        return
    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        errors.append(
            {
                "path": path,
                "code": "invalid_enum",
                "message": "Value is not in the allowed set",
                "allowedValues": enum_values,
            }
        )
    if expected_type == "object" and isinstance(value, dict):
        validate_object(value, schema, path, strict, errors, warnings)
    if expected_type == "array" and isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_node(item, item_schema, f"{path}[{index}]", strict, errors, warnings)


def validate_object(
    value: dict[str, Any],
    schema: dict[str, object],
    path: str,
    strict: bool,
    errors: list[dict[str, object]],
    warnings: list[dict[str, object]],
) -> None:
    required = schema.get("required")
    properties = schema.get("properties")
    additional_properties = schema.get("additionalProperties", True)
    required_fields = (
        [field for field in required if isinstance(field, str)]
        if isinstance(required, list)
        else []
    )
    property_schemas = properties if isinstance(properties, dict) else {}
    for field in required_fields:
        if field not in value:
            errors.append(
                {
                    "path": f"{path}.{field}",
                    "code": "missing_required_field",
                    "message": "Required field is missing",
                }
            )
    for field, field_value in value.items():
        nested_schema = property_schemas.get(field)
        if isinstance(nested_schema, dict):
            validate_node(field_value, nested_schema, f"{path}.{field}", strict, errors, warnings)
        elif additional_properties is False or strict:
            errors.append(
                {
                    "path": f"{path}.{field}",
                    "code": "unknown_field",
                    "message": "Field is not defined by the contract",
                }
            )
        else:
            warnings.append(
                {
                    "path": f"{path}.{field}",
                    "code": "unknown_field",
                    "message": "Field is not defined by the contract",
                }
            )


def value_matches_type(value: object, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, int | float | Decimal) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    if expected_type == "market_number":
        return is_market_number(value)
    return True


def is_market_number(value: object) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, int | float | Decimal | str):
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return False
        return decimal_value.is_finite()
    return False


def summarize_payload(payload: dict[str, Any] | list[Any]) -> dict[str, object]:
    if isinstance(payload, dict):
        keys = sorted(str(key) for key in payload)
        return {
            "payloadType": "object",
            "fieldCount": len(keys),
            "topLevelKeys": keys[:50],
            "truncatedTopLevelKeys": max(len(keys) - 50, 0),
        }
    return {
        "payloadType": "array",
        "itemCount": len(payload),
        "firstItemType": type(payload[0]).__name__ if payload else None,
    }
