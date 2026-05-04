from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from app.modules.daily_briefs.models import DailyBriefItemType, DailyBriefPriority

FORBIDDEN_DAILY_BRIEF_PHRASES = (
    "buy now",
    "sell now",
    "enter trade",
    "exit trade",
    "take profit",
    "stop loss",
    "use leverage",
    "guaranteed",
    "profit",
    "win rate",
    "trade alert",
)

JsonValue = dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None

SECTION_BY_ITEM_TYPE = {
    DailyBriefItemType.REVIEW_FIRST: "review_first",
    DailyBriefItemType.NEEDS_CONFIRMATION: "needs_confirmation",
    DailyBriefItemType.AVOID_CONDITION: "avoid_conditions",
    DailyBriefItemType.STALE_DATA: "data_freshness",
    DailyBriefItemType.DATA_QUALITY_ISSUE: "data_freshness",
    DailyBriefItemType.OUTCOME_UPDATE: "outcome_updates",
    DailyBriefItemType.WATCH_NEXT: "watch_next",
    DailyBriefItemType.PENDING_ACTION: "pending_actions",
    DailyBriefItemType.MARKET_CONTEXT: "market_context",
    DailyBriefItemType.JOURNAL_FOLLOW_UP: "watch_next",
}

SECTION_NAMES = (
    "review_first",
    "needs_confirmation",
    "avoid_conditions",
    "data_freshness",
    "outcome_updates",
    "watch_next",
    "pending_actions",
    "market_context",
)

PRIORITY_RANK = {
    DailyBriefPriority.URGENT: 0,
    DailyBriefPriority.HIGH: 1,
    DailyBriefPriority.NORMAL: 2,
    DailyBriefPriority.LOW: 3,
}


def sanitize_daily_brief_text(value: str) -> str:
    sanitized = value
    replacements = {
        "buy now": "review bullish context",
        "sell now": "review bearish context",
        "enter trade": "review setup context",
        "exit trade": "review invalidation context",
        "take profit": "review target context zone",
        "stop loss": "review invalidation context",
        "use leverage": "review exposure context",
        "guaranteed": "high certainty claim",
        "profit": "result",
        "win rate": "historical alignment",
        "trade alert": "review item",
    }
    for phrase in FORBIDDEN_DAILY_BRIEF_PHRASES:
        sanitized = replace_case_insensitive(sanitized, phrase, replacements[phrase])
    return sanitized


def validate_daily_brief_text(value: str) -> str:
    sanitized = sanitize_daily_brief_text(value)
    lowered = sanitized.lower()
    for phrase in FORBIDDEN_DAILY_BRIEF_PHRASES:
        if phrase in lowered:
            return replace_case_insensitive(sanitized, phrase, "review context")
    return sanitized


def replace_case_insensitive(value: str, target: str, replacement: str) -> str:
    lowered = value.lower()
    target_lowered = target.lower()
    result = value
    start = lowered.find(target_lowered)
    while start != -1:
        end = start + len(target)
        result = result[:start] + replacement + result[end:]
        lowered = result.lower()
        start = lowered.find(target_lowered, start + len(replacement))
    return result


def safe_label(value: str | None, fallback: str = "review context") -> str:
    if value is None or value.strip() == "":
        return fallback
    return validate_daily_brief_text(value.replace("_", " ").strip())


def safe_bias_label(value: str | None) -> str:
    normalized = (value or "").lower()
    if normalized == "bullish":
        return "bullish bias"
    if normalized == "bearish":
        return "bearish bias"
    if normalized == "neutral":
        return "neutral"
    return "no directional signal"


def safe_outcome_label(label: str) -> str:
    mapping = {
        "continuation": "observed follow-through",
        "partial_follow_through": "partial observed follow-through",
        "no_follow_through": "no observed follow-through",
        "reversal": "observed reversal",
        "sideways_after_signal": "sideways context after signal",
        "insufficient_data": "insufficient future data",
        "not_directional": "not directional",
        "failed": "evaluation failed",
    }
    return mapping.get(label, safe_label(label))


def safe_action_label(action_type: str) -> str:
    mapping = {
        "evaluate_outcome_after_horizon": "evaluate outcome after horizon",
        "run_replay": "review replay path",
        "run_news_correlation": "review news correlation context",
        "wait_for_more_final_candles": "wait for more final candles",
        "request_human_review": "request human review",
        "no_action": "no backend follow-up",
    }
    return mapping.get(action_type, safe_label(action_type))


def priority_from_label(label: str | None) -> DailyBriefPriority:
    normalized = (label or "").lower()
    if normalized in {"urgent", "urgent_review", "critical"}:
        return DailyBriefPriority.URGENT
    if normalized in {"high", "blocked", "poor", "failed", "failing"}:
        return DailyBriefPriority.HIGH
    if normalized in {"low"}:
        return DailyBriefPriority.LOW
    return DailyBriefPriority.NORMAL


def priority_from_score(score: Decimal | None) -> DailyBriefPriority:
    if score is None:
        return DailyBriefPriority.NORMAL
    if score >= Decimal("0.90"):
        return DailyBriefPriority.URGENT
    if score >= Decimal("0.75"):
        return DailyBriefPriority.HIGH
    if score < Decimal("0.40"):
        return DailyBriefPriority.LOW
    return DailyBriefPriority.NORMAL


def context_message(value: object, fallback: str) -> str:
    if isinstance(value, dict):
        for key in ("message", "summary", "reason", "label", "condition", "description", "title"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return validate_daily_brief_text(item)
    if isinstance(value, str) and value.strip():
        return validate_daily_brief_text(value)
    return fallback


def item_sort_key(
    priority: DailyBriefPriority, item_type: DailyBriefItemType, title: str
) -> tuple[int, str, str]:
    type_rank = {
        DailyBriefItemType.REVIEW_FIRST: "0",
        DailyBriefItemType.NEEDS_CONFIRMATION: "1",
        DailyBriefItemType.AVOID_CONDITION: "2",
        DailyBriefItemType.STALE_DATA: "3",
        DailyBriefItemType.DATA_QUALITY_ISSUE: "4",
        DailyBriefItemType.OUTCOME_UPDATE: "5",
        DailyBriefItemType.MARKET_CONTEXT: "6",
        DailyBriefItemType.WATCH_NEXT: "7",
        DailyBriefItemType.PENDING_ACTION: "8",
        DailyBriefItemType.JOURNAL_FOLLOW_UP: "9",
    }[item_type]
    return (PRIORITY_RANK[priority], type_rank, title)


def to_json_value(value: object) -> JsonValue:
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [to_json_value(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
