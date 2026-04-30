import re
from dataclasses import dataclass

BLOCKED_DIRECT_PHRASES = (
    "buy now",
    "sell now",
    "enter now",
    "exit now",
    "take profit",
    "stop loss",
    "use leverage",
    "guaranteed",
    "guarantee",
    "risk-free",
    "sure win",
    "cannot lose",
    "profit guaranteed",
    "this will go up",
    "this will go down",
    "execute trade",
    "place order",
    "long now",
    "short now",
    "go long",
    "go short",
)
INSTRUCTION_PATTERNS = (
    r"\b(?:should|must|need to|please)\s+buy\b",
    r"\b(?:should|must|need to|please)\s+sell\b",
    r"\b(?:should|must|need to|please)\s+enter\b",
    r"\b(?:should|must|need to|please)\s+exit\b",
)


@dataclass(frozen=True)
class ReasoningSafetyResult:
    passed: bool
    blocked_terms: list[str]


def check_reasoning_safety(output_text: str) -> ReasoningSafetyResult:
    normalized = " ".join(output_text.lower().split())
    blocked_terms = [
        phrase for phrase in BLOCKED_DIRECT_PHRASES if phrase_in_text(normalized, phrase)
    ]
    blocked_terms.extend(
        pattern for pattern in INSTRUCTION_PATTERNS if re.search(pattern, normalized) is not None
    )
    return ReasoningSafetyResult(passed=not blocked_terms, blocked_terms=blocked_terms)


def phrase_in_text(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None
