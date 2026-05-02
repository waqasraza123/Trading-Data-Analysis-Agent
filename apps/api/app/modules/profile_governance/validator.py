from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.modules.strategy_profiles.seeds import DEFAULT_STRATEGY_PROFILES


SUPPORTED_PATTERN_TYPES = {
    pattern
    for profile in DEFAULT_STRATEGY_PROFILES
    for pattern in (*profile.allowed_patterns, *profile.excluded_patterns)
}
WEIGHT_WARNING_TOLERANCE = Decimal("0.0500")
EXECUTION_KEYWORDS = {
    "broker",
    "broker_id",
    "broker_account",
    "execution",
    "execution_config",
    "trade_execution",
    "trade",
    "trading",
    "auto_trade",
    "order",
    "order_type",
    "position",
    "position_size",
    "quantity",
    "size",
    "lot",
    "lot_size",
    "margin",
    "stop_loss",
    "take_profit",
}
TRADE_ACTION_KEYS = {
    "buy",
    "sell",
    "entry",
    "exit",
    "leverage",
}


@dataclass(frozen=True)
class ProfileValidationIssue:
    field: str
    code: str
    message: str

    def to_dict(self) -> dict[str, object]:
        return {"field": self.field, "code": self.code, "message": self.message}


@dataclass(frozen=True)
class ProfileValidationResult:
    errors: list[ProfileValidationIssue]
    warnings: list[ProfileValidationIssue]

    @property
    def status(self) -> str:
        if self.errors:
            return "invalid"
        if self.warnings:
            return "valid_with_warnings"
        return "valid"

    def errors_json(self) -> list[dict[str, object]]:
        return [issue.to_dict() for issue in self.errors]

    def warnings_json(self) -> list[dict[str, object]]:
        return [issue.to_dict() for issue in self.warnings]


def validate_profile_config(
    draft_key: str,
    draft_version: str,
    config: dict[str, object],
) -> ProfileValidationResult:
    errors: list[ProfileValidationIssue] = []
    warnings: list[ProfileValidationIssue] = []
    if draft_key.strip() == "":
        errors.append(issue("draft_key", "required", "draft_key is required"))
    if draft_version.strip() == "":
        errors.append(issue("draft_version", "required", "draft_version is required"))

    blocked_key_paths = find_blocked_key_paths(config)
    for path, key in blocked_key_paths:
        errors.append(
            issue(
                path,
                "execution_key_not_allowed",
                f"Strategy profiles must not include execution or trade action field '{key}'",
            )
        )

    allowed_patterns = string_list(config.get("allowed_patterns_json"))
    excluded_patterns = string_list(config.get("excluded_patterns_json"), allow_missing=True)
    if not allowed_patterns:
        errors.append(
            issue(
                "allowed_patterns_json",
                "required",
                "allowed_patterns_json must contain at least one pattern",
            )
        )
    if allowed_patterns is None:
        errors.append(
            issue("allowed_patterns_json", "invalid_type", "allowed_patterns_json must be a list")
        )
    if excluded_patterns is None:
        errors.append(
            issue("excluded_patterns_json", "invalid_type", "excluded_patterns_json must be a list")
        )
    if allowed_patterns and excluded_patterns:
        overlap = sorted(set(allowed_patterns) & set(excluded_patterns))
        if set(allowed_patterns).issubset(set(excluded_patterns)):
            errors.append(
                issue(
                    "excluded_patterns_json",
                    "fully_overlaps_allowed_patterns",
                    "excluded patterns must not fully overlap allowed patterns",
                )
            )
        elif overlap:
            warnings.append(
                issue(
                    "excluded_patterns_json",
                    "overlaps_allowed_patterns",
                    f"excluded patterns also appear in allowed patterns: {', '.join(overlap)}",
                )
            )

    validate_supported_patterns("allowed_patterns_json", allowed_patterns, errors)
    validate_supported_patterns("excluded_patterns_json", excluded_patterns, errors)
    validate_probability_field("minimum_candidate_strength", config, errors)
    validate_probability_field("minimum_confidence", config, errors)
    validate_component_weights(config.get("component_weights_json"), errors, warnings)
    validate_object_field("risk_filters_json", config, errors)
    validate_object_field("no_signal_rules_json", config, errors)
    return ProfileValidationResult(errors=errors, warnings=warnings)


def validate_supported_patterns(
    field: str,
    patterns: list[str] | None,
    errors: list[ProfileValidationIssue],
) -> None:
    if patterns is None:
        return
    unsupported = sorted(pattern for pattern in patterns if pattern not in SUPPORTED_PATTERN_TYPES)
    if unsupported:
        errors.append(
            issue(
                field,
                "unsupported_pattern_type",
                f"Unsupported pattern type(s): {', '.join(unsupported)}",
            )
        )


def validate_probability_field(
    field: str,
    config: dict[str, object],
    errors: list[ProfileValidationIssue],
) -> None:
    value = decimal_value(config.get(field))
    if value is None:
        errors.append(issue(field, "invalid_number", f"{field} must be a decimal between 0 and 1"))
        return
    if value < Decimal("0") or value > Decimal("1"):
        errors.append(issue(field, "out_of_range", f"{field} must be between 0 and 1"))


def validate_component_weights(
    raw_weights: object,
    errors: list[ProfileValidationIssue],
    warnings: list[ProfileValidationIssue],
) -> None:
    if not isinstance(raw_weights, dict) or not raw_weights:
        errors.append(
            issue(
                "component_weights_json",
                "invalid_type",
                "component_weights_json must be a non-empty object",
            )
        )
        return
    total = Decimal("0")
    weight_error_count = len(errors)
    for component, raw_value in raw_weights.items():
        value = decimal_value(raw_value)
        field = f"component_weights_json.{component}"
        if value is None:
            errors.append(issue(field, "invalid_number", "component weight must be a decimal"))
            continue
        if value < Decimal("0"):
            errors.append(issue(field, "negative_weight", "component weight must be non-negative"))
            continue
        total += value
    if len(errors) > weight_error_count:
        return
    if abs(total - Decimal("1")) > WEIGHT_WARNING_TOLERANCE:
        warnings.append(
            issue(
                "component_weights_json",
                "weights_sum_not_close_to_one",
                f"component weights should sum close to 1.0; current sum is {total}",
            )
        )


def validate_object_field(
    field: str,
    config: dict[str, object],
    errors: list[ProfileValidationIssue],
) -> None:
    if not isinstance(config.get(field), dict):
        errors.append(issue(field, "invalid_type", f"{field} must be an object"))


def find_blocked_key_paths(value: object, path: str = "") -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child_value in value.items():
            key_text = str(key)
            normalized = normalize_key(key_text)
            child_path = f"{path}.{key_text}" if path else key_text
            if normalized in EXECUTION_KEYWORDS or normalized in TRADE_ACTION_KEYS:
                matches.append((child_path, key_text))
            matches.extend(find_blocked_key_paths(child_value, child_path))
    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            child_path = f"{path}[{index}]"
            matches.extend(find_blocked_key_paths(child_value, child_path))
    return matches


def normalize_key(value: str) -> str:
    return value.strip().replace("-", "_").replace(" ", "_").lower()


def string_list(raw_value: object, allow_missing: bool = False) -> list[str] | None:
    if raw_value is None and allow_missing:
        return []
    if not isinstance(raw_value, list):
        return None
    if not all(isinstance(item, str) and item.strip() for item in raw_value):
        return None
    return [item.strip() for item in raw_value]


def decimal_value(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def issue(field: str, code: str, message: str) -> ProfileValidationIssue:
    return ProfileValidationIssue(field=field, code=code, message=message)
