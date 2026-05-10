from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.action_plans.models import ReasoningActionItem
from app.modules.news.models import NewsEvent, SignalNewsCorrelation
from app.modules.signal_digests.models import (
    SignalDigestItemType,
    SignalDigestPriority,
    SignalDigestType,
)
from app.modules.signal_digests.repository import (
    SignalDigestActionContext,
    SignalDigestDataQualityContext,
    SignalDigestMemoryContext,
    SignalDigestNewsContext,
    SignalDigestOutcomeContext,
    SignalDigestQualityContext,
    SignalDigestReadinessContext,
    SignalDigestScheduledScanContext,
    SignalDigestSignalContext,
)
from app.modules.signals.models import Signal
from app.modules.symbols.models import Symbol

FORBIDDEN_DIGEST_PHRASES = (
    "trade now",
    "guaranteed",
    "profit",
    "win rate",
    "leverage",
    "buy",
    "sell",
    "enter",
    "exit",
)

JsonValue = dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None


@dataclass(frozen=True)
class SignalDigestBuildInput:
    workspace_id: UUID
    digest_type: SignalDigestType
    period_start: datetime
    period_end: datetime
    timezone: str
    filters_json: dict[str, object]
    max_items: int
    high_confidence_threshold: Decimal
    stale_data_priority: SignalDigestPriority
    session_label: str | None = None


@dataclass(frozen=True)
class SignalDigestArtifacts:
    signals: list[SignalDigestSignalContext]
    outcomes: list[SignalDigestOutcomeContext]
    news_context: list[SignalDigestNewsContext]
    pending_actions: list[SignalDigestActionContext]
    data_quality_warnings: list[SignalDigestDataQualityContext]
    stale_memory: list[SignalDigestMemoryContext]
    quality_reviews: list[SignalDigestQualityContext]
    readiness_reviews: list[SignalDigestReadinessContext]
    due_scan_configs: list[SignalDigestScheduledScanContext]


@dataclass(frozen=True)
class SignalDigestDraftItem:
    item_type: SignalDigestItemType
    priority: SignalDigestPriority
    title: str
    summary: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    symbol_id: UUID | None = None
    signal_id: UUID | None = None
    setup_context_id: UUID | None = None
    analysis_run_id: UUID | None = None
    outcome_id: UUID | None = None
    action_item_id: UUID | None = None
    news_event_id: UUID | None = None


@dataclass(frozen=True)
class BuiltSignalDigest:
    title: str
    summary_json: dict[str, object]
    section_counts_json: dict[str, int]
    warnings_json: list[dict[str, object]]
    items: list[SignalDigestDraftItem]


class SignalDigestBuilder:
    def build(
        self,
        digest_input: SignalDigestBuildInput,
        artifacts: SignalDigestArtifacts,
    ) -> BuiltSignalDigest:
        items = self.build_items(digest_input, artifacts)
        section_counts = count_sections(items)
        warnings = build_digest_warnings(artifacts, digest_input.max_items, len(items))
        return BuiltSignalDigest(
            title=build_digest_title(digest_input),
            summary_json=build_executive_summary(artifacts, items, digest_input),
            section_counts_json=section_counts,
            warnings_json=warnings,
            items=items[: digest_input.max_items],
        )

    def build_items(
        self,
        digest_input: SignalDigestBuildInput,
        artifacts: SignalDigestArtifacts,
    ) -> list[SignalDigestDraftItem]:
        candidates: list[SignalDigestDraftItem] = []
        candidates.extend(self.top_directional_bias_items(digest_input, artifacts.signals))
        candidates.extend(self.no_signal_items(artifacts.signals))
        candidates.extend(self.outcome_update_items(artifacts.outcomes))
        candidates.extend(self.news_context_items(artifacts.news_context))
        candidates.extend(self.pending_action_items(artifacts.pending_actions))
        candidates.extend(self.due_scan_items(artifacts.due_scan_configs))
        candidates.extend(self.data_quality_items(artifacts.data_quality_warnings))
        candidates.extend(self.stale_memory_items(digest_input, artifacts.stale_memory))
        candidates.extend(self.quality_review_items(artifacts.quality_reviews))
        candidates.extend(self.readiness_review_items(artifacts.readiness_reviews))
        candidates.extend(self.watch_condition_items(artifacts.signals, artifacts.stale_memory))
        return sorted(candidates, key=digest_item_sort_key)[: digest_input.max_items]

    def top_directional_bias_items(
        self,
        digest_input: SignalDigestBuildInput,
        signals: list[SignalDigestSignalContext],
    ) -> list[SignalDigestDraftItem]:
        directional = [
            signal_context
            for signal_context in signals
            if signal_context.signal.classification_status == "signal"
            and signal_context.signal.bias in {"bullish", "bearish"}
            and signal_context.signal.confidence_score >= digest_input.high_confidence_threshold
        ]
        directional.sort(
            key=lambda item: (
                item.signal.confidence_score,
                item.evidence_count,
                item.signal.created_at,
            ),
            reverse=True,
        )
        return [build_top_bias_item(item) for item in directional]

    def no_signal_items(
        self,
        signals: list[SignalDigestSignalContext],
    ) -> list[SignalDigestDraftItem]:
        items: list[SignalDigestDraftItem] = []
        for signal_context in signals:
            signal = signal_context.signal
            if signal.classification_status in {"no_signal", "unclear", "insufficient_evidence"}:
                items.append(build_no_signal_item(signal_context))
            if has_conflict_context(signal):
                items.append(build_conflict_item(signal_context))
        return items

    def outcome_update_items(
        self,
        outcomes: list[SignalDigestOutcomeContext],
    ) -> list[SignalDigestDraftItem]:
        return [build_outcome_item(outcome_context) for outcome_context in outcomes]

    def news_context_items(
        self,
        news_context: list[SignalDigestNewsContext],
    ) -> list[SignalDigestDraftItem]:
        return [build_news_item(context) for context in news_context]

    def pending_action_items(
        self,
        pending_actions: list[SignalDigestActionContext],
    ) -> list[SignalDigestDraftItem]:
        return [build_action_item(context) for context in pending_actions]

    def due_scan_items(
        self,
        due_scan_configs: list[SignalDigestScheduledScanContext],
    ) -> list[SignalDigestDraftItem]:
        return [build_due_scan_item(context) for context in due_scan_configs]

    def data_quality_items(
        self,
        data_quality_warnings: list[SignalDigestDataQualityContext],
    ) -> list[SignalDigestDraftItem]:
        return [build_data_quality_item(context) for context in data_quality_warnings]

    def stale_memory_items(
        self,
        digest_input: SignalDigestBuildInput,
        stale_memory: list[SignalDigestMemoryContext],
    ) -> list[SignalDigestDraftItem]:
        return [build_stale_memory_item(context, digest_input) for context in stale_memory]

    def quality_review_items(
        self,
        quality_reviews: list[SignalDigestQualityContext],
    ) -> list[SignalDigestDraftItem]:
        return [build_quality_review_item(context) for context in quality_reviews]

    def readiness_review_items(
        self,
        readiness_reviews: list[SignalDigestReadinessContext],
    ) -> list[SignalDigestDraftItem]:
        return [build_readiness_review_item(context) for context in readiness_reviews]

    def watch_condition_items(
        self,
        signals: list[SignalDigestSignalContext],
        stale_memory: list[SignalDigestMemoryContext],
    ) -> list[SignalDigestDraftItem]:
        items: list[SignalDigestDraftItem] = []
        for signal_context in signals[:20]:
            items.append(build_signal_watch_condition_item(signal_context))
        for memory_context in stale_memory[:20]:
            items.append(build_memory_watch_condition_item(memory_context))
        return items


def build_executive_summary(
    artifacts: SignalDigestArtifacts,
    items: list[SignalDigestDraftItem],
    digest_input: SignalDigestBuildInput,
) -> dict[str, object]:
    signals = [context.signal for context in artifacts.signals]
    return to_json_value(
        {
            "period": {
                "start": digest_input.period_start,
                "end": digest_input.period_end,
                "timezone": digest_input.timezone,
                "digestType": digest_input.digest_type.value,
                "sessionLabel": digest_input.session_label,
            },
            "counts": {
                "totalSignals": len(signals),
                "bullish": count_signals(signals, "bullish", "signal"),
                "bearish": count_signals(signals, "bearish", "signal"),
                "neutral": count_signals(signals, "neutral", None),
                "noSignal": count_no_signal(signals),
                "reviewRecommended": count_item_type(
                    items,
                    SignalDigestItemType.REVIEW_RECOMMENDED,
                ),
                "staleOrDegradedData": count_stale_or_degraded(artifacts),
                "recentOutcomeUpdates": len(artifacts.outcomes),
            },
            "safeLanguage": {
                "deterministicArtifactsOnly": True,
                "noNotifications": True,
                "noFinancialAdvice": True,
                "noBrokerExecution": True,
                "noLlmClassification": True,
            },
            "filters": digest_input.filters_json,
        }
    )


def build_digest_title(digest_input: SignalDigestBuildInput) -> str:
    label = digest_input.digest_type.value.replace("_", " ")
    if digest_input.session_label is not None:
        label = f"{digest_input.session_label.replace('_', ' ')} session"
    return sanitize_digest_text(
        f"Signal digest {label} {digest_input.period_start.date().isoformat()}"
    )


def build_top_bias_item(context: SignalDigestSignalContext) -> SignalDigestDraftItem:
    signal = context.signal
    symbol_label = symbol_name(context.symbol)
    bias_label = "bullish bias" if signal.bias == "bullish" else "bearish bias"
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.TOP_BIAS,
        priority=priority_from_confidence(signal.confidence_score),
        title=sanitize_digest_text(f"{symbol_label} {bias_label}"),
        summary=sanitize_digest_text(
            f"{symbol_label} has fresh {bias_label} context with deterministic "
            f"confidence {format_decimal(signal.confidence_score)} and "
            f"{context.evidence_count} evidence entries."
        ),
        tags=["directional_bias", signal.bias, signal.timeframe, signal.confidence_label],
        metadata=signal_metadata(signal, context),
        symbol_id=signal.symbol_id,
        signal_id=signal.id,
        setup_context_id=context.setup_context_id,
        analysis_run_id=signal.analysis_run_id,
    )


def build_no_signal_item(context: SignalDigestSignalContext) -> SignalDigestDraftItem:
    signal = context.signal
    symbol_label = symbol_name(context.symbol)
    reason = signal.no_signal_reason or signal.classification_status
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.NO_SIGNAL,
        priority=SignalDigestPriority.NORMAL,
        title=sanitize_digest_text(f"{symbol_label} no directional signal"),
        summary=sanitize_digest_text(
            f"{symbol_label} has no directional signal for {signal.timeframe}. "
            f"Review context: {humanize_label(reason)}."
        ),
        tags=["no_directional_signal", signal.timeframe, humanize_label(reason)],
        metadata=signal_metadata(signal, context),
        symbol_id=signal.symbol_id,
        signal_id=signal.id,
        setup_context_id=context.setup_context_id,
        analysis_run_id=signal.analysis_run_id,
    )


def build_conflict_item(context: SignalDigestSignalContext) -> SignalDigestDraftItem:
    signal = context.signal
    symbol_label = symbol_name(context.symbol)
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.CONFLICT,
        priority=SignalDigestPriority.HIGH,
        title=sanitize_digest_text(f"{symbol_label} conflict context"),
        summary=sanitize_digest_text(
            f"{symbol_label} has conflicting or range-bound evidence. "
            "Review recommended before relying on directional context."
        ),
        tags=["conflict", signal.timeframe],
        metadata=signal_metadata(signal, context),
        symbol_id=signal.symbol_id,
        signal_id=signal.id,
        setup_context_id=context.setup_context_id,
        analysis_run_id=signal.analysis_run_id,
    )


def build_outcome_item(context: SignalDigestOutcomeContext) -> SignalDigestDraftItem:
    outcome = context.outcome
    symbol_label = symbol_name(context.symbol)
    label = safe_outcome_label(outcome.outcome_label)
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.OUTCOME_UPDATE,
        priority=SignalDigestPriority.NORMAL,
        title=sanitize_digest_text(f"{symbol_label} outcome update"),
        summary=sanitize_digest_text(
            f"{symbol_label} completed a {outcome.horizon_minutes} minute outcome review: {label}."
        ),
        tags=["outcome_update", outcome.outcome_label, outcome.timeframe],
        metadata={
            "outcomeLabel": outcome.outcome_label,
            "evaluationStatus": outcome.evaluation_status,
            "horizonMinutes": outcome.horizon_minutes,
            "timeframe": outcome.timeframe,
            "futureCandleCount": outcome.future_candle_count,
        },
        symbol_id=outcome.symbol_id,
        signal_id=outcome.signal_id,
        analysis_run_id=outcome.analysis_run_id,
        outcome_id=outcome.id,
    )


def build_news_item(context: SignalDigestNewsContext) -> SignalDigestDraftItem:
    event = context.event
    correlation = context.correlation
    symbol_label = symbol_name(context.symbol)
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.NEWS_CONTEXT,
        priority=news_priority(correlation, event),
        title=sanitize_digest_text(f"{symbol_label} possible news context"),
        summary=sanitize_digest_text(
            f"{event.title} has {correlation.correlation_label} possible correlation "
            f"context with {symbol_label}; this does not imply causation."
        ),
        tags=["news_context", correlation.correlation_label, event.importance],
        metadata={
            "correlationLabel": correlation.correlation_label,
            "correlationScore": correlation.correlation_score,
            "directionAlignment": correlation.direction_alignment,
            "volatilityReaction": correlation.volatility_reaction,
            "eventImportance": event.importance,
            "eventTime": event.event_time,
        },
        symbol_id=context.signal.symbol_id if context.signal is not None else event.symbol_id,
        signal_id=correlation.signal_id,
        analysis_run_id=correlation.analysis_run_id,
        news_event_id=event.id,
    )


def build_action_item(context: SignalDigestActionContext) -> SignalDigestDraftItem:
    action = context.action_item
    symbol_label = symbol_name(context.symbol)
    action_label = safe_action_label(action.action_type)
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.PENDING_ACTION,
        priority=priority_from_action(action),
        title=sanitize_digest_text(f"{symbol_label} pending backend follow-up"),
        summary=sanitize_digest_text(
            f"Pending backend follow-up for {symbol_label}: {action_label}. "
            "Digest generation does not run this follow-up."
        ),
        tags=["pending_backend_follow_up", action.action_type, action.status],
        metadata={
            "actionType": action.action_type,
            "status": action.status,
            "dueAt": action.due_at,
            "horizonMinutes": action.horizon_minutes,
        },
        symbol_id=context.signal.symbol_id if context.signal is not None else None,
        signal_id=action.signal_id,
        analysis_run_id=action.analysis_run_id,
        action_item_id=action.id,
    )


def build_due_scan_item(context: SignalDigestScheduledScanContext) -> SignalDigestDraftItem:
    config = context.scan_config
    label = symbol_name(context.symbol) if context.symbol is not None else watchlist_name(context)
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.PENDING_ACTION,
        priority=SignalDigestPriority.NORMAL,
        title=sanitize_digest_text(f"{label} scheduled scan due"),
        summary=sanitize_digest_text(
            f"Scheduled backend scan is due for {label}. Digest generation only lists it."
        ),
        tags=["scheduled_scan_due", config.scan_mode],
        metadata={
            "scanConfigId": config.id,
            "scanMode": config.scan_mode,
            "nextRunAt": config.next_run_at,
            "timeframe": config.timeframe,
        },
        symbol_id=config.symbol_id,
    )


def build_data_quality_item(context: SignalDigestDataQualityContext) -> SignalDigestDraftItem:
    run = context.run
    symbol_label = symbol_name(context.symbol)
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.DATA_QUALITY_WARNING,
        priority=quality_priority(run.quality_label),
        title=sanitize_digest_text(f"{symbol_label} data quality warning"),
        summary=sanitize_digest_text(
            f"{symbol_label} data quality is {humanize_label(run.quality_label)} "
            f"for {run.timeframe or 'the requested scope'}."
        ),
        tags=["data_quality", run.quality_label, run.scope_type],
        metadata={
            "qualityLabel": run.quality_label,
            "qualityScore": run.quality_score,
            "scopeType": run.scope_type,
            "findingCount": run.finding_count,
            "timeframe": run.timeframe,
        },
        symbol_id=run.symbol_id,
    )


def build_stale_memory_item(
    context: SignalDigestMemoryContext,
    digest_input: SignalDigestBuildInput,
) -> SignalDigestDraftItem:
    snapshot = context.snapshot
    symbol_label = symbol_name(context.symbol)
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.STALE_DATA,
        priority=digest_input.stale_data_priority,
        title=sanitize_digest_text(f"{symbol_label} stale data"),
        summary=sanitize_digest_text(
            f"{symbol_label} market memory reports {snapshot.freshness_label} freshness "
            f"and {snapshot.data_quality_label} data quality for {snapshot.timeframe}."
        ),
        tags=["stale_data", snapshot.freshness_label, snapshot.data_quality_label],
        metadata={
            "freshnessLabel": snapshot.freshness_label,
            "dataQualityLabel": snapshot.data_quality_label,
            "latestFinalCandleTime": snapshot.latest_final_candle_time,
            "timeframe": snapshot.timeframe,
            "warnings": snapshot.warnings_json,
        },
        symbol_id=snapshot.symbol_id,
        signal_id=snapshot.latest_signal_id,
        analysis_run_id=snapshot.latest_analysis_run_id,
        outcome_id=snapshot.latest_outcome_id,
    )


def build_quality_review_item(context: SignalDigestQualityContext) -> SignalDigestDraftItem:
    quality_run = context.quality_run
    symbol_label = symbol_name(context.symbol)
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.REVIEW_RECOMMENDED,
        priority=review_priority(quality_run.quality_label),
        title=sanitize_digest_text(f"{symbol_label} review recommended"),
        summary=sanitize_digest_text(
            f"{symbol_label} quality gate label is {humanize_label(quality_run.quality_label)}. "
            "Review recommended for deterministic evidence consistency."
        ),
        tags=["review_recommended", "quality_gate", quality_run.quality_label],
        metadata={
            "qualityRunId": quality_run.id,
            "qualityLabel": quality_run.quality_label,
            "qualityScore": quality_run.quality_score,
            "sourceType": quality_run.source_type,
        },
        symbol_id=context.signal.symbol_id if context.signal is not None else None,
        signal_id=quality_run.signal_id,
        analysis_run_id=quality_run.analysis_run_id,
    )


def build_readiness_review_item(context: SignalDigestReadinessContext) -> SignalDigestDraftItem:
    assessment = context.assessment
    symbol_label = symbol_name(context.symbol)
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.REVIEW_RECOMMENDED,
        priority=review_priority(assessment.readiness_label),
        title=sanitize_digest_text(f"{symbol_label} readiness review"),
        summary=sanitize_digest_text(
            f"{symbol_label} readiness label is {humanize_label(assessment.readiness_label)}. "
            "Review recommended before using this context operationally."
        ),
        tags=["review_recommended", "decision_readiness", assessment.readiness_label],
        metadata={
            "assessmentId": assessment.id,
            "readinessLabel": assessment.readiness_label,
            "readinessScore": assessment.readiness_score,
            "sourceType": assessment.source_type,
            "blockers": assessment.blockers_json,
            "warnings": assessment.warnings_json,
        },
        symbol_id=context.signal.symbol_id if context.signal is not None else None,
        signal_id=assessment.signal_id,
        analysis_run_id=assessment.analysis_run_id,
    )


def build_signal_watch_condition_item(context: SignalDigestSignalContext) -> SignalDigestDraftItem:
    signal = context.signal
    symbol_label = symbol_name(context.symbol)
    summary = (
        "Wait for final candle close and review evidence."
        if signal.classification_status == "signal"
        else "Inspect data quality and review evidence before relying on directional context."
    )
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.WATCH_CONDITION,
        priority=SignalDigestPriority.LOW,
        title=sanitize_digest_text(f"{symbol_label} watch condition"),
        summary=sanitize_digest_text(f"{symbol_label}: {summary}"),
        tags=["watch_condition", signal.timeframe, signal.classification_status],
        metadata={
            "condition": summary,
            "timeframe": signal.timeframe,
            "classificationStatus": signal.classification_status,
        },
        symbol_id=signal.symbol_id,
        signal_id=signal.id,
        setup_context_id=context.setup_context_id,
        analysis_run_id=signal.analysis_run_id,
    )


def build_memory_watch_condition_item(context: SignalDigestMemoryContext) -> SignalDigestDraftItem:
    snapshot = context.snapshot
    symbol_label = symbol_name(context.symbol)
    return SignalDigestDraftItem(
        item_type=SignalDigestItemType.WATCH_CONDITION,
        priority=SignalDigestPriority.LOW,
        title=sanitize_digest_text(f"{symbol_label} data watch condition"),
        summary=sanitize_digest_text(
            f"{symbol_label}: inspect data quality before relying on current context."
        ),
        tags=["watch_condition", "data_quality", snapshot.timeframe],
        metadata={
            "condition": "inspect data quality",
            "timeframe": snapshot.timeframe,
            "freshnessLabel": snapshot.freshness_label,
            "dataQualityLabel": snapshot.data_quality_label,
        },
        symbol_id=snapshot.symbol_id,
        signal_id=snapshot.latest_signal_id,
        analysis_run_id=snapshot.latest_analysis_run_id,
    )


def digest_item_sort_key(item: SignalDigestDraftItem) -> tuple[int, str, str]:
    priority_rank = {
        SignalDigestPriority.URGENT: 0,
        SignalDigestPriority.HIGH: 1,
        SignalDigestPriority.NORMAL: 2,
        SignalDigestPriority.LOW: 3,
    }[item.priority]
    type_rank = {
        SignalDigestItemType.TOP_BIAS: "0",
        SignalDigestItemType.REVIEW_RECOMMENDED: "1",
        SignalDigestItemType.CONFLICT: "2",
        SignalDigestItemType.STALE_DATA: "3",
        SignalDigestItemType.DATA_QUALITY_WARNING: "4",
        SignalDigestItemType.OUTCOME_UPDATE: "5",
        SignalDigestItemType.NEWS_CONTEXT: "6",
        SignalDigestItemType.PENDING_ACTION: "7",
        SignalDigestItemType.NO_SIGNAL: "8",
        SignalDigestItemType.WATCH_CONDITION: "9",
    }[item.item_type]
    return (priority_rank, type_rank, item.title)


def count_sections(items: list[SignalDigestDraftItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.item_type.value] = counts.get(item.item_type.value, 0) + 1
    return counts


def build_digest_warnings(
    artifacts: SignalDigestArtifacts,
    max_items: int,
    item_count: int,
) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    if item_count > max_items:
        warnings.append(
            {
                "code": "digest_item_limit_applied",
                "severity": "low",
                "message": "Digest items were capped by maxItems",
            }
        )
    if not artifacts.signals and not artifacts.stale_memory:
        warnings.append(
            {
                "code": "no_recent_signal_context",
                "severity": "medium",
                "message": "No recent signal or market memory context matched the filters",
            }
        )
    return warnings


def count_signals(signals: list[Signal], bias: str, status: str | None) -> int:
    return sum(1 for signal in signals if signal.bias == bias and status_matches(signal, status))


def status_matches(signal: Signal, status: str | None) -> bool:
    return status is None or signal.classification_status == status


def count_no_signal(signals: list[Signal]) -> int:
    return sum(
        1
        for signal in signals
        if signal.classification_status in {"no_signal", "unclear", "insufficient_evidence"}
    )


def count_item_type(
    items: list[SignalDigestDraftItem],
    item_type: SignalDigestItemType,
) -> int:
    return sum(1 for item in items if item.item_type == item_type)


def count_stale_or_degraded(artifacts: SignalDigestArtifacts) -> int:
    return len(artifacts.stale_memory) + len(artifacts.data_quality_warnings)


def signal_metadata(signal: Signal, context: SignalDigestSignalContext) -> dict[str, object]:
    return {
        "bias": signal.bias,
        "classificationStatus": signal.classification_status,
        "confidenceScore": signal.confidence_score,
        "confidenceLabel": signal.confidence_label,
        "evidenceCount": context.evidence_count,
        "riskCount": context.risk_count,
        "setupContextId": context.setup_context_id,
        "timeframe": signal.timeframe,
        "patternType": signal.pattern_type,
        "noSignalReason": signal.no_signal_reason,
        "createdAt": signal.created_at,
    }


def has_conflict_context(signal: Signal) -> bool:
    candidates = [
        signal.no_signal_reason,
        signal.range_state,
        signal.volatility_state,
        signal.summary,
    ]
    return any(
        value is not None
        and any(token in value.lower() for token in ("conflict", "fakeout", "chop", "range"))
        for value in candidates
    )


def priority_from_confidence(score: Decimal) -> SignalDigestPriority:
    if score >= Decimal("0.85"):
        return SignalDigestPriority.HIGH
    return SignalDigestPriority.NORMAL


def priority_from_action(action: ReasoningActionItem) -> SignalDigestPriority:
    if action.status in {"due", "failed"}:
        return SignalDigestPriority.HIGH
    if action.priority == "high":
        return SignalDigestPriority.HIGH
    if action.priority == "low":
        return SignalDigestPriority.LOW
    return SignalDigestPriority.NORMAL


def quality_priority(label: str) -> SignalDigestPriority:
    if label in {"poor", "insufficient_data"}:
        return SignalDigestPriority.HIGH
    return SignalDigestPriority.NORMAL


def review_priority(label: str) -> SignalDigestPriority:
    if label in {"blocked", "inconsistent", "insufficient_context"}:
        return SignalDigestPriority.HIGH
    return SignalDigestPriority.NORMAL


def news_priority(
    correlation: SignalNewsCorrelation,
    event: NewsEvent,
) -> SignalDigestPriority:
    if correlation.correlation_label == "strong" or event.importance in {"high", "critical"}:
        return SignalDigestPriority.HIGH
    return SignalDigestPriority.NORMAL


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
    return mapping.get(label, humanize_label(label))


def safe_action_label(action_type: str) -> str:
    mapping = {
        "evaluate_outcome_after_horizon": "evaluate outcome after horizon",
        "run_replay": "review replay path",
        "run_news_correlation": "run news correlation",
        "wait_for_more_final_candles": "wait for more final candles",
        "request_human_review": "request human review",
        "no_action": "no backend follow-up",
    }
    return mapping.get(action_type, humanize_label(action_type))


def symbol_name(symbol: Symbol | None) -> str:
    if symbol is None:
        return "Workspace context"
    return symbol.symbol


def watchlist_name(context: SignalDigestScheduledScanContext) -> str:
    if context.watchlist is None:
        return "watchlist context"
    return context.watchlist.name


def humanize_label(value: str) -> str:
    return value.replace("_", " ").strip()


def format_decimal(value: Decimal) -> str:
    return f"{value:.2f}"


def sanitize_digest_text(value: str) -> str:
    sanitized = value
    replacements = {
        "trade now": "act immediately",
        "guaranteed": "certain",
        "profit": "result",
        "win rate": "historical alignment",
        "leverage": "exposure",
        "buy": "bullish action",
        "sell": "bearish action",
        "enter": "start",
        "exit": "stop",
    }
    for phrase in FORBIDDEN_DIGEST_PHRASES:
        sanitized = replace_case_insensitive(sanitized, phrase, replacements[phrase])
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


def to_json_value(value: object) -> JsonValue:
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_json_value(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value
