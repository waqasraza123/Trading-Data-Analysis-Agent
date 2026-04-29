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
    "financial advice",
    "this will go up",
    "this will go down",
    "profit guaranteed",
    "guaranteed profit",
    "take this trade",
    "enter now",
    "exit now",
)

ALLOWED_CONTEXT_PHRASES: tuple[str, ...] = ("not financial advice",)


@dataclass(frozen=True)
class SafetyCheckResult:
    passed: bool
    blocked_terms: list[str]


def check_explanation_safety(text: str) -> SafetyCheckResult:
    normalized = normalize_text(text)
    for allowed in ALLOWED_CONTEXT_PHRASES:
        normalized = normalized.replace(allowed, "")
    blocked_terms = [phrase for phrase in BLOCKED_PHRASES if contains_phrase(normalized, phrase)]
    return SafetyCheckResult(passed=not blocked_terms, blocked_terms=blocked_terms)


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None
