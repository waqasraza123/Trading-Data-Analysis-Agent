import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.modules.llm_explanations.models import LlmExplanationGroundingStatus

NUMERIC_PATTERN = re.compile(r"(?<!\d)(-?\d+(?:\.\d+)?)(?!\d)", re.IGNORECASE)
NEWS_CAUSATION_PHRASES = (
    "definitely caused",
    "caused the move",
    "caused this move",
    "caused by",
    "confirmed reason",
    "guaranteed reaction",
    "definitely drove",
    "definitely triggered",
)
NEWS_KEYWORDS = ("news", "event", "announcement", "press", "statement")
ENTRY_ACTION_PHRASES = (
    "buy",
    "sell",
    "enter",
    "exit",
    "take this trade",
    "must enter",
    "exit now",
    "enter now",
)
GUARANTEE_PHRASES = ("guarantee", "guaranteed", "certain", "certainly")
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
)


@dataclass(frozen=True)
class GroundingCheckResult:
    status: LlmExplanationGroundingStatus
    issues: list[str]


def check_explanation_grounding(
    input_json: dict[str, object],
    output_text: str,
) -> GroundingCheckResult:
    issues: list[str] = []
    normalized_output = " ".join(output_text.lower().split())
    allowed_numbers = _collect_allowed_numbers(input_json)
    invented_numbers = _extract_invented_numbers(allowed_numbers, normalized_output)
    issues.extend([f"invented numeric value: {value}" for value in invented_numbers])
    if invented_numbers:
        return GroundingCheckResult(
            status=LlmExplanationGroundingStatus.FAILED,
            issues=issues,
        )

    if _mentions_other_pattern(input_json, normalized_output):
        issues.append("output mentions a different pattern than persisted input")
    if _mentions_entry_action(normalized_output):
        issues.append("output contains trade instruction language")
    if _mentions_news(normalized_output):
        if not _has_news_correlations(input_json):
            issues.append("output mentions news/event without persisted news correlation evidence")
        elif not _mentions_known_news_descriptor(input_json, normalized_output):
            issues.append("output mentions news/event without matching persisted event descriptor")
        if _mentions_news_causation(normalized_output):
            issues.append("output states causation from correlation")
    if _mentions_guarantee(normalized_output):
        issues.append("output claims a guaranteed outcome")

    if not issues:
        return GroundingCheckResult(
            status=LlmExplanationGroundingStatus.GROUNDED,
            issues=[],
        )
    if any(_contains_issue_marker(issue) for issue in issues):
        status = LlmExplanationGroundingStatus.FAILED
    else:
        status = LlmExplanationGroundingStatus.QUESTIONABLE
    return GroundingCheckResult(status=status, issues=issues)


def _contains_issue_marker(issue: str) -> bool:
    return any(
        marker in issue
        for marker in (
            "invented numeric value",
            "different pattern",
            "without persisted news",
            "without matching persisted event",
            "causation from correlation",
            "trade instruction",
            "guaranteed outcome",
        )
    )


def _collect_allowed_numbers(value: object) -> set[str]:
    normalized_numbers: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and (
                "time" in key.lower()
                or "timestamp" in key.lower()
                or key.lower().endswith("_at")
                or key.lower().endswith("_id")
            ):
                continue
            normalized_numbers.update(_collect_allowed_numbers(item))
        return normalized_numbers
    if isinstance(value, list):
        for item in value:
            normalized_numbers.update(_collect_allowed_numbers(item))
        return normalized_numbers
    if isinstance(value, str):
        if _is_numeric_text(value):
            normalized_numbers.add(_normalize_number(value))
        return normalized_numbers
    if isinstance(value, int | float):
        normalized_numbers.add(_normalize_number(str(value)))
        return normalized_numbers
    if isinstance(value, Decimal):
        normalized_numbers.add(_normalize_number(str(value)))
    return normalized_numbers


def _extract_invented_numbers(
    allowed_numbers: set[str],
    output_text: str,
) -> list[str]:
    found = set(NUMERIC_PATTERN.findall(output_text))
    invented: list[str] = []
    for raw_value in found:
        normalized = _normalize_number(raw_value)
        if normalized and normalized not in allowed_numbers:
            invented.append(raw_value)
    return invented


def _is_numeric_text(value: str) -> bool:
    try:
        Decimal(value)
    except (TypeError, InvalidOperation):
        return False
    return True


def _normalize_number(value: str) -> str:
    try:
        normalized = str(Decimal(value).normalize())
    except (TypeError, InvalidOperation):
        return ""
    if normalized in {"-0", "0E+0"}:
        return "0"
    return normalized


def _has_news_correlations(input_json: dict[str, object]) -> bool:
    correlations = _get_nested_value(input_json, "news_correlations")
    return bool(correlations)


def _mentions_news_without_input_news(
    input_json: dict[str, object],
    normalized_output: str,
) -> bool:
    has_news = _has_news_correlations(input_json)
    return not has_news and any(keyword in normalized_output for keyword in NEWS_KEYWORDS)


def _mentions_news(normalized_output: str) -> bool:
    return any(keyword in normalized_output for keyword in NEWS_KEYWORDS)


def _mentions_known_news_descriptor(
    input_json: dict[str, object],
    normalized_output: str,
) -> bool:
    descriptors = _collect_news_descriptors(input_json)
    return any(descriptor in normalized_output for descriptor in descriptors)


def _collect_news_descriptors(input_json: dict[str, object]) -> set[str]:
    correlations = _get_nested_value(input_json, "news_correlations")
    descriptors: set[str] = set()
    if not isinstance(correlations, list):
        return descriptors
    for item in correlations:
        if not isinstance(item, dict):
            continue
        for key in ("eventTitle", "eventType", "currency", "asset", "importance"):
            value = item.get(key)
            if isinstance(value, str):
                normalized = " ".join(value.replace("_", " ").lower().split())
                if normalized:
                    descriptors.add(normalized)
    return descriptors


def _mentions_other_pattern(
    input_json: dict[str, object],
    normalized_output: str,
) -> bool:
    pattern_type = _get_nested_value(input_json, "pattern_type")
    if pattern_type is None or not isinstance(pattern_type, str):
        return any(pattern in normalized_output for pattern in KNOWN_PATTERN_TERMS)
    normalized_pattern = pattern_type.replace("_", " ")
    mentioned_patterns = {
        pattern for pattern in KNOWN_PATTERN_TERMS if pattern in normalized_output
    }
    return bool(mentioned_patterns and normalized_pattern not in mentioned_patterns)


def _mentions_entry_action(normalized_output: str) -> bool:
    return any(
        re.search(rf"\b{re.escape(phrase)}\b", normalized_output) is not None
        for phrase in ENTRY_ACTION_PHRASES
    )


def _mentions_guarantee(normalized_output: str) -> bool:
    return any(phrase in normalized_output for phrase in GUARANTEE_PHRASES)


def _mentions_news_causation(normalized_output: str) -> bool:
    return any(phrase in normalized_output for phrase in NEWS_CAUSATION_PHRASES)


def _get_nested_value(
    payload: dict[str, object],
    key: str,
) -> object:
    if key in payload:
        return payload[key]
    for value in payload.values():
        if isinstance(value, dict):
            nested = _get_nested_value(value, key)
            if nested is not None:
                return nested
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    nested = _get_nested_value(item, key)
                    if nested is not None:
                        return nested
    return None
