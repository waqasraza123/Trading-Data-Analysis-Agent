from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.reasoning.models import ReasoningGroundingStatus
from app.modules.reasoning.parser import ALLOWED_BACKEND_ACTIONS

NUMERIC_PATTERN = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")
NEWS_KEYWORDS = ("news", "event", "announcement", "headline", "cpi", "fomc", "rate decision")
NEWS_CAUSATION_PHRASES = (
    "caused the move",
    "caused this move",
    "caused by",
    "definitely caused",
    "confirmed reason",
    "definitely drove",
    "definitely triggered",
)
CERTAINTY_PHRASES = (
    "will definitely",
    "is certain",
    "certainly will",
    "guaranteed",
    "cannot fail",
)
KNOWN_PATTERN_TERMS = (
    "bullish breakout",
    "bearish breakdown",
    "bullish continuation",
    "bearish continuation",
    "bullish reversal",
    "bearish reversal",
    "sideways range",
    "low volatility chop",
    "unclear structure",
    "fakeout",
    "breakout",
    "breakdown",
)


@dataclass(frozen=True)
class ReasoningGroundingResult:
    status: ReasoningGroundingStatus
    issues: list[str]


def check_reasoning_grounding(
    input_json: dict[str, Any],
    output_json: dict[str, Any],
    output_text: str,
) -> ReasoningGroundingResult:
    serialized_output = json.dumps(output_json, sort_keys=True).lower()
    normalized_output = " ".join(f"{serialized_output} {output_text}".lower().split())
    issues: list[str] = []
    invented_numbers = invented_numeric_values(input_json, normalized_output)
    issues.extend([f"invented numeric value: {value}" for value in invented_numbers])
    if mentions_other_pattern(input_json, normalized_output):
        issues.append("output mentions a pattern not present in input")
    if mentions_other_strategy(input_json, normalized_output):
        issues.append("output mentions a strategy profile not present in input")
    if mentions_news(normalized_output):
        if not has_news(input_json):
            issues.append("output mentions news when no news correlations exist")
        if mentions_news_causation(normalized_output):
            issues.append("output says news caused the move")
    if mentions_certainty(normalized_output):
        issues.append("output says a future scenario is certain")
    issues.extend(backend_action_issues(output_json))
    if invents_outcome_history(input_json, output_json):
        issues.append("output invents outcome history when none exists")
    if not issues:
        return ReasoningGroundingResult(ReasoningGroundingStatus.GROUNDED, [])
    return ReasoningGroundingResult(ReasoningGroundingStatus.FAILED, issues)


def invented_numeric_values(input_json: dict[str, Any], output_text: str) -> list[str]:
    allowed = collect_allowed_numbers(input_json)
    invented: list[str] = []
    for value in set(NUMERIC_PATTERN.findall(output_text)):
        normalized = normalize_number(value)
        if normalized and normalized not in allowed:
            invented.append(value)
    return sorted(invented)


def collect_allowed_numbers(value: object) -> set[str]:
    numbers: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            if "time" in key_text or key_text.endswith("id") or key_text.endswith("at"):
                continue
            numbers.update(collect_allowed_numbers(item))
    elif isinstance(value, list):
        for item in value:
            numbers.update(collect_allowed_numbers(item))
    elif isinstance(value, str) and is_numeric_text(value):
        numbers.add(normalize_number(value))
    elif isinstance(value, int | float | Decimal):
        numbers.add(normalize_number(str(value)))
    return numbers


def is_numeric_text(value: str) -> bool:
    try:
        Decimal(value)
    except (InvalidOperation, ValueError):
        return False
    return True


def normalize_number(value: str) -> str:
    try:
        normalized = str(Decimal(value).normalize())
    except (InvalidOperation, ValueError):
        return ""
    if normalized in {"-0", "0E+0"}:
        return "0"
    return normalized


def mentions_other_pattern(input_json: dict[str, Any], output_text: str) -> bool:
    pattern = input_json.get("patternType")
    if not isinstance(pattern, str) or not pattern:
        return any(term in output_text for term in KNOWN_PATTERN_TERMS)
    allowed = pattern.replace("_", " ").lower()
    mentioned = {term for term in KNOWN_PATTERN_TERMS if term in output_text}
    return bool(mentioned and allowed not in mentioned)


def mentions_other_strategy(input_json: dict[str, Any], output_text: str) -> bool:
    strategy = input_json.get("strategyProfileKey")
    if not isinstance(strategy, str) or not strategy:
        return "strategy profile" in output_text
    if strategy.lower() in output_text:
        return False
    return "strategy profile" in output_text and "stored strategy profile" not in output_text


def mentions_news(output_text: str) -> bool:
    return any(keyword in output_text for keyword in NEWS_KEYWORDS)


def has_news(input_json: dict[str, Any]) -> bool:
    value = input_json.get("newsCorrelations")
    return isinstance(value, list) and bool(value)


def mentions_news_causation(output_text: str) -> bool:
    return any(phrase in output_text for phrase in NEWS_CAUSATION_PHRASES)


def mentions_certainty(output_text: str) -> bool:
    return any(phrase in output_text for phrase in CERTAINTY_PHRASES)


def backend_action_issues(output_json: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    scenarios = output_json.get("scenarios")
    if not isinstance(scenarios, list):
        return issues
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        actions = scenario.get("suggestedBackendActions")
        if not isinstance(actions, list):
            continue
        for action in actions:
            if isinstance(action, str) and action not in ALLOWED_BACKEND_ACTIONS:
                issues.append(f"output mentions backend action not allowed: {action}")
    return issues


def invents_outcome_history(input_json: dict[str, Any], output_json: dict[str, Any]) -> bool:
    history = input_json.get("outcomeHistory")
    has_history = (
        isinstance(history, dict)
        and isinstance(history.get("items"), list)
        and any(
            isinstance(item, dict) and item.get("matchingOutcomeCount", 0) != 0
            for item in history["items"]
        )
    )
    if has_history:
        return False
    scenarios = output_json.get("scenarios")
    if not isinstance(scenarios, list):
        return False
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            continue
        outcome_history = scenario.get("outcomeHistory")
        if isinstance(outcome_history, dict) and outcome_history.get("available") is True:
            return True
    return False
