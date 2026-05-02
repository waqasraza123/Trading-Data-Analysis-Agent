from typing import Any

from app.modules.strategy_profiles.models import StrategyProfile


def strategy_profile_config(profile: StrategyProfile | None) -> dict[str, object]:
    if profile is None:
        return {}
    return {
        "allowed_patterns_json": profile.allowed_patterns_json,
        "excluded_patterns_json": profile.excluded_patterns_json,
        "minimum_candidate_strength": str(profile.minimum_candidate_strength),
        "minimum_confidence": str(profile.minimum_confidence),
        "component_weights_json": profile.component_weights_json,
        "risk_filters_json": profile.risk_filters_json,
        "no_signal_rules_json": profile.no_signal_rules_json,
    }


def diff_profile_config(
    base_config: dict[str, object],
    proposed_config: dict[str, object],
) -> dict[str, object]:
    return {
        "allowedPatterns": list_diff(
            base_config.get("allowed_patterns_json"),
            proposed_config.get("allowed_patterns_json"),
        ),
        "excludedPatterns": list_diff(
            base_config.get("excluded_patterns_json"),
            proposed_config.get("excluded_patterns_json"),
        ),
        "minimumThresholds": field_changes(
            base_config,
            proposed_config,
            ["minimum_candidate_strength", "minimum_confidence"],
        ),
        "componentWeights": object_changes(
            base_config.get("component_weights_json"),
            proposed_config.get("component_weights_json"),
        ),
        "riskFilters": object_changes(
            base_config.get("risk_filters_json"),
            proposed_config.get("risk_filters_json"),
        ),
        "noSignalRules": object_changes(
            base_config.get("no_signal_rules_json"),
            proposed_config.get("no_signal_rules_json"),
        ),
    }


def list_diff(base_value: object, proposed_value: object) -> dict[str, list[str]]:
    base_items = {str(item) for item in base_value} if isinstance(base_value, list) else set()
    proposed_items = (
        {str(item) for item in proposed_value} if isinstance(proposed_value, list) else set()
    )
    return {
        "added": sorted(proposed_items - base_items),
        "removed": sorted(base_items - proposed_items),
    }


def field_changes(
    base_config: dict[str, object],
    proposed_config: dict[str, object],
    fields: list[str],
) -> dict[str, dict[str, object | None]]:
    changes: dict[str, dict[str, object | None]] = {}
    for field in fields:
        base_value = normalize_scalar(base_config.get(field))
        proposed_value = normalize_scalar(proposed_config.get(field))
        if base_value != proposed_value:
            changes[field] = {"from": base_value, "to": proposed_value}
    return changes


def object_changes(base_value: object, proposed_value: object) -> dict[str, Any]:
    base = base_value if isinstance(base_value, dict) else {}
    proposed = proposed_value if isinstance(proposed_value, dict) else {}
    added = {key: proposed[key] for key in sorted(proposed.keys() - base.keys())}
    removed = {key: base[key] for key in sorted(base.keys() - proposed.keys())}
    changed = {
        key: {"from": base[key], "to": proposed[key]}
        for key in sorted(base.keys() & proposed.keys())
        if normalize_scalar(base[key]) != normalize_scalar(proposed[key])
    }
    return {"added": added, "removed": removed, "changed": changed}


def normalize_scalar(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (dict, list, bool, int, float)):
        return value
    return str(value)
