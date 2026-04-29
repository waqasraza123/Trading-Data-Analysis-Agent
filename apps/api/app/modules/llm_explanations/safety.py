import re
from dataclasses import dataclass

BLOCKED_PHRASES: tuple[str, ...] = (
    "buy now",
    "sell now",
    "guaranteed",
    "guarantee",
    "risk-free",
    "sure win",
    "must enter",
    "cannot lose",
    "use leverage",
    "take this trade",
    "enter now",
    "exit now",
    "guaranteed profit",
    "profit guaranteed",
    "this will go up",
    "this will go down",
)


@dataclass(frozen=True)
class SafetyCheckResult:
    passed: bool
    blocked_terms: list[str]


def check_explanation_safety(text: str) -> SafetyCheckResult:
    normalized = " ".join(text.lower().split())
    blocked_terms = [phrase for phrase in BLOCKED_PHRASES if _contains_phrase(normalized, phrase)]
    return SafetyCheckResult(passed=not blocked_terms, blocked_terms=blocked_terms)


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None
