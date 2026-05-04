from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.daily_briefs.models import DailyBriefItemType, DailyBriefPriority, DailyBriefType
from app.modules.daily_briefs.repository import (
    DailyBriefActionContext,
    DailyBriefDataQualityContext,
    DailyBriefDigestContext,
    DailyBriefJournalContext,
    DailyBriefLatestCandleContext,
    DailyBriefMarketContext,
    DailyBriefMemoryContext,
    DailyBriefOutcomeContext,
    DailyBriefProviderHealthContext,
    DailyBriefScanContext,
    DailyBriefSignalContext,
)
from app.modules.daily_briefs.sections import (
    SECTION_BY_ITEM_TYPE,
    SECTION_NAMES,
    context_message,
    item_sort_key,
    priority_from_label,
    priority_from_score,
    safe_action_label,
    safe_bias_label,
    safe_label,
    safe_outcome_label,
    to_json_value,
    validate_daily_brief_text,
)


@dataclass(frozen=True)
class DailyBriefBuildInput:
    workspace_id: UUID
    brief_type: DailyBriefType
    period_start: datetime
    period_end: datetime
    timezone: str
    filters_json: dict[str, object]
    max_items: int
    review_first_limit: int
    outcome_update_limit: int
    action_item_limit: int
    session_label: str | None = None
    watchlist_id: UUID | None = None


@dataclass(frozen=True)
class DailyBriefArtifacts:
    digest_context: DailyBriefDigestContext | None
    priority_signals: list[DailyBriefSignalContext]
    recent_signals: list[DailyBriefSignalContext]
    memory_contexts: list[DailyBriefMemoryContext]
    provider_health: list[DailyBriefProviderHealthContext]
    latest_candles: list[DailyBriefLatestCandleContext]
    data_quality: list[DailyBriefDataQualityContext]
    outcomes: list[DailyBriefOutcomeContext]
    pending_actions: list[DailyBriefActionContext]
    due_scans: list[DailyBriefScanContext]
    market_contexts: list[DailyBriefMarketContext]
    journal_contexts: list[DailyBriefJournalContext]


@dataclass(frozen=True)
class DailyBriefDraftItem:
    item_type: DailyBriefItemType
    priority: DailyBriefPriority
    title: str
    summary: str
    reason: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    symbol_id: UUID | None = None
    signal_id: UUID | None = None
    analysis_run_id: UUID | None = None
    outcome_id: UUID | None = None
    action_item_id: UUID | None = None
    setup_context_id: UUID | None = None
    source_type: str | None = None
    source_id: UUID | None = None


@dataclass(frozen=True)
class BuiltDailyBrief:
    digest_id: UUID | None
    summary_json: dict[str, object]
    sections_json: dict[str, object]
    warnings_json: list[dict[str, object]]
    items: list[DailyBriefDraftItem]


class DailyBriefBuilder:
    def build(
        self,
        brief_input: DailyBriefBuildInput,
        artifacts: DailyBriefArtifacts,
    ) -> BuiltDailyBrief:
        items = self.build_items(brief_input, artifacts)
        sorted_items = sorted(
            unique_items(items),
            key=lambda item: item_sort_key(item.priority, item.item_type, item.title),
        )[: brief_input.max_items]
        sections = build_sections(sorted_items, artifacts)
        warnings = build_warnings(artifacts, len(items), brief_input.max_items)
        return BuiltDailyBrief(
            digest_id=artifacts.digest_context.digest.id
            if artifacts.digest_context is not None
            else None,
            summary_json=build_summary(brief_input, artifacts, sorted_items),
            sections_json=sections,
            warnings_json=warnings,
            items=sorted_items,
        )

    def build_items(
        self,
        brief_input: DailyBriefBuildInput,
        artifacts: DailyBriefArtifacts,
    ) -> list[DailyBriefDraftItem]:
        signals = merge_signal_contexts(artifacts.priority_signals, artifacts.recent_signals)
        items: list[DailyBriefDraftItem] = []
        items.extend(build_review_first_items(signals, brief_input.review_first_limit))
        items.extend(build_needs_confirmation_items(signals))
        items.extend(
            build_avoid_items(signals, artifacts.memory_contexts, artifacts.provider_health)
        )
        items.extend(
            build_data_freshness_items(
                artifacts.memory_contexts,
                artifacts.provider_health,
                artifacts.latest_candles,
                artifacts.data_quality,
            )
        )
        items.extend(build_outcome_items(artifacts.outcomes, brief_input.outcome_update_limit))
        items.extend(
            build_watch_next_items(signals, artifacts.memory_contexts, artifacts.journal_contexts)
        )
        items.extend(
            build_pending_action_items(
                artifacts.pending_actions, artifacts.due_scans, brief_input.action_item_limit
            )
        )
        items.extend(build_market_context_items(artifacts.market_contexts))
        return items


def build_summary(
    brief_input: DailyBriefBuildInput,
    artifacts: DailyBriefArtifacts,
    items: list[DailyBriefDraftItem],
) -> dict[str, object]:
    reviewed_symbol_ids = {
        *[
            context.signal.symbol_id
            for context in merge_signal_contexts(
                artifacts.priority_signals, artifacts.recent_signals
            )
        ],
        *[context.snapshot.symbol_id for context in artifacts.memory_contexts],
        *[context.symbol_id for context in artifacts.latest_candles],
    }
    fresh_symbol_ids = {
        context.snapshot.symbol_id
        for context in artifacts.memory_contexts
        if context.snapshot.freshness_label == "fresh"
    }
    fresh_symbol_ids.update(
        context.symbol_id
        for context in artifacts.provider_health
        if context.symbol_id is not None and context.freshness_label == "fresh"
    )
    stale_symbol_ids = {
        context.snapshot.symbol_id
        for context in artifacts.memory_contexts
        if is_stale_or_degraded(
            context.snapshot.freshness_label, context.snapshot.data_quality_label
        )
    }
    stale_symbol_ids.update(
        context.symbol_id
        for context in artifacts.provider_health
        if context.symbol_id is not None and is_provider_stale_or_degraded(context)
    )
    return to_json_value(
        {
            "period": {
                "start": brief_input.period_start,
                "end": brief_input.period_end,
                "timezone": brief_input.timezone,
                "briefType": brief_input.brief_type.value,
                "sessionLabel": brief_input.session_label,
                "watchlistId": brief_input.watchlist_id,
            },
            "counts": {
                "totalSymbolsReviewed": len(reviewed_symbol_ids),
                "freshSymbols": len(fresh_symbol_ids),
                "staleDegradedSymbols": len(stale_symbol_ids),
                "reviewFirstCount": count_item_type(items, DailyBriefItemType.REVIEW_FIRST),
                "needsConfirmationCount": count_item_type(
                    items, DailyBriefItemType.NEEDS_CONFIRMATION
                ),
                "avoidConditionCount": count_item_type(items, DailyBriefItemType.AVOID_CONDITION),
                "recentOutcomeCount": count_item_type(items, DailyBriefItemType.OUTCOME_UPDATE),
                "pendingBackendActionCount": count_item_type(
                    items, DailyBriefItemType.PENDING_ACTION
                ),
            },
            "sourceArtifacts": {
                "signalDigestId": artifacts.digest_context.digest.id
                if artifacts.digest_context
                else None,
                "prioritySignalCount": len(artifacts.priority_signals),
                "recentSignalCount": len(artifacts.recent_signals),
                "marketMemoryCount": len(artifacts.memory_contexts),
                "providerHealthCount": len(artifacts.provider_health),
                "outcomeCount": len(artifacts.outcomes),
                "marketContextCount": len(artifacts.market_contexts),
                "journalEntryCount": len(artifacts.journal_contexts),
            },
            "safeLanguage": {
                "deterministicArtifactsOnly": True,
                "noFinancialAdvice": True,
                "noBrokerExecution": True,
                "noActionExecution": True,
                "noNotifications": True,
                "noLlmCalls": True,
            },
            "filters": brief_input.filters_json,
        }
    )


def build_review_first_items(
    signals: list[DailyBriefSignalContext],
    limit: int,
) -> list[DailyBriefDraftItem]:
    candidates = [context for context in signals if is_review_first_context(context)]
    candidates.sort(key=review_first_sort_key, reverse=True)
    return [build_review_first_item(context) for context in candidates[:limit]]


def is_review_first_context(context: DailyBriefSignalContext) -> bool:
    priority = context.priority_score
    signal = context.signal
    if priority is not None and priority.review_bucket == "high_quality_context":
        return True
    if priority is not None and priority.priority_label in {"urgent_review", "high"}:
        return True
    if signal.classification_status == "signal" and signal.bias in {"bullish", "bearish"}:
        return signal.confidence_score >= Decimal("0.7000")
    return False


def review_first_sort_key(context: DailyBriefSignalContext) -> tuple[Decimal, Decimal, datetime]:
    priority_score = (
        context.priority_score.priority_score
        if context.priority_score is not None
        else Decimal("0")
    )
    setup_quality = (
        context.setup_context.setup_quality_score
        if context.setup_context is not None
        else Decimal("0")
    )
    return (
        priority_score,
        max(context.signal.confidence_score, setup_quality),
        context.signal.created_at,
    )


def build_review_first_item(context: DailyBriefSignalContext) -> DailyBriefDraftItem:
    signal = context.signal
    symbol = context.symbol.symbol
    bias = safe_bias_label(signal.bias)
    priority = (
        priority_from_label(context.priority_score.priority_label)
        if context.priority_score is not None
        else priority_from_score(signal.confidence_score)
    )
    return DailyBriefDraftItem(
        item_type=DailyBriefItemType.REVIEW_FIRST,
        priority=priority,
        title=validate_daily_brief_text(f"{symbol} review first"),
        summary=validate_daily_brief_text(
            f"{symbol} has {bias} with {safe_label(signal.confidence_label)} "
            "confidence and fresh setup context."
        ),
        reason=review_reason(context),
        tags=["review_first", signal.timeframe, signal.bias, signal.confidence_label],
        metadata=signal_metadata(context),
        symbol_id=signal.symbol_id,
        signal_id=signal.id,
        analysis_run_id=signal.analysis_run_id,
        setup_context_id=context.setup_context.id if context.setup_context is not None else None,
        source_type="signal_priority" if context.priority_score is not None else "signal",
        source_id=context.priority_score.id if context.priority_score is not None else signal.id,
    )


def build_needs_confirmation_items(
    signals: list[DailyBriefSignalContext],
) -> list[DailyBriefDraftItem]:
    items: list[DailyBriefDraftItem] = []
    for context in signals:
        signal = context.signal
        priority = context.priority_score
        setup = context.setup_context
        readiness = context.readiness
        needs_confirmation = priority is not None and priority.review_bucket in {
            "needs_confirmation",
            "conflicted",
            "review_required",
        }
        needs_confirmation = needs_confirmation or signal.confidence_label == "medium"
        needs_confirmation = needs_confirmation or (
            setup is not None
            and (
                setup.setup_quality_label in {"mixed_context", "review_required"}
                or bool(setup.wait_conditions_json)
            )
        )
        needs_confirmation = needs_confirmation or (
            readiness is not None
            and readiness.readiness_label in {"review_recommended", "insufficient_context"}
        )
        if not needs_confirmation:
            continue
        symbol = context.symbol.symbol
        reason = confirmation_reason(context)
        items.append(
            DailyBriefDraftItem(
                item_type=DailyBriefItemType.NEEDS_CONFIRMATION,
                priority=priority_from_label(
                    priority.priority_label if priority is not None else "normal"
                ),
                title=validate_daily_brief_text(f"{symbol} needs confirmation"),
                summary=validate_daily_brief_text(
                    f"{symbol} needs confirmation before relying on directional context."
                ),
                reason=reason,
                tags=["needs_confirmation", signal.timeframe, signal.confidence_label],
                metadata=signal_metadata(context),
                symbol_id=signal.symbol_id,
                signal_id=signal.id,
                analysis_run_id=signal.analysis_run_id,
                setup_context_id=setup.id if setup is not None else None,
                source_type="setup_context" if setup is not None else "signal",
                source_id=setup.id if setup is not None else signal.id,
            )
        )
    return items


def build_avoid_items(
    signals: list[DailyBriefSignalContext],
    memory_contexts: list[DailyBriefMemoryContext],
    provider_health: list[DailyBriefProviderHealthContext],
) -> list[DailyBriefDraftItem]:
    items: list[DailyBriefDraftItem] = []
    for context in signals:
        signal = context.signal
        setup = context.setup_context
        priority = context.priority_score
        avoid = signal.classification_status in {"no_signal", "unclear", "insufficient_evidence"}
        avoid = avoid or has_conflict_context(
            signal.summary, signal.no_signal_reason, signal.range_state
        )
        avoid = avoid or (
            priority is not None
            and priority.review_bucket in {"avoid_or_no_directional_signal", "stale_or_data_issue"}
        )
        avoid = avoid or (
            setup is not None
            and (setup.setup_quality_label == "avoid_condition" or bool(setup.avoid_reasons_json))
        )
        if avoid:
            symbol = context.symbol.symbol
            items.append(
                DailyBriefDraftItem(
                    item_type=DailyBriefItemType.AVOID_CONDITION,
                    priority=DailyBriefPriority.HIGH
                    if priority and priority.priority_label in {"avoid", "stale"}
                    else DailyBriefPriority.NORMAL,
                    title=validate_daily_brief_text(f"{symbol} avoid condition"),
                    summary=validate_daily_brief_text(
                        f"{symbol} has avoid condition context or no directional signal."
                    ),
                    reason=avoid_reason(context),
                    tags=["avoid_condition", signal.timeframe, signal.classification_status],
                    metadata=signal_metadata(context),
                    symbol_id=signal.symbol_id,
                    signal_id=signal.id,
                    analysis_run_id=signal.analysis_run_id,
                    setup_context_id=setup.id if setup is not None else None,
                    source_type="setup_context" if setup is not None else "signal",
                    source_id=setup.id if setup is not None else signal.id,
                )
            )
    for context in memory_contexts:
        snapshot = context.snapshot
        if is_stale_or_degraded(snapshot.freshness_label, snapshot.data_quality_label):
            items.append(
                DailyBriefDraftItem(
                    item_type=DailyBriefItemType.AVOID_CONDITION,
                    priority=DailyBriefPriority.NORMAL,
                    title=validate_daily_brief_text(
                        f"{context.symbol.symbol} data avoid condition"
                    ),
                    summary=validate_daily_brief_text(
                        f"{context.symbol.symbol} has stale data or low data quality."
                    ),
                    reason=validate_daily_brief_text(
                        f"Freshness is {safe_label(snapshot.freshness_label)} "
                        f"and quality is {safe_label(snapshot.data_quality_label)}."
                    ),
                    tags=["avoid_condition", "stale_data", snapshot.timeframe],
                    metadata=memory_metadata(context),
                    symbol_id=snapshot.symbol_id,
                    signal_id=snapshot.latest_signal_id,
                    analysis_run_id=snapshot.latest_analysis_run_id,
                    outcome_id=snapshot.latest_outcome_id,
                    source_type="market_memory",
                    source_id=snapshot.id,
                )
            )
    for context in provider_health:
        if is_provider_stale_or_degraded(context):
            symbol = context.symbol or "Workspace context"
            items.append(
                DailyBriefDraftItem(
                    item_type=DailyBriefItemType.AVOID_CONDITION,
                    priority=priority_from_label(context.status),
                    title=validate_daily_brief_text(f"{symbol} provider avoid condition"),
                    summary=validate_daily_brief_text(
                        f"{symbol} provider health indicates stale data or degraded status."
                    ),
                    reason=validate_daily_brief_text(context.summary),
                    tags=["avoid_condition", "provider_health", context.status],
                    metadata=provider_metadata(context),
                    symbol_id=context.symbol_id,
                    source_type="provider_health",
                    source_id=context.snapshot_id,
                )
            )
    return items


def build_data_freshness_items(
    memory_contexts: list[DailyBriefMemoryContext],
    provider_health: list[DailyBriefProviderHealthContext],
    latest_candles: list[DailyBriefLatestCandleContext],
    data_quality: list[DailyBriefDataQualityContext],
) -> list[DailyBriefDraftItem]:
    items: list[DailyBriefDraftItem] = []
    for context in memory_contexts:
        snapshot = context.snapshot
        if is_stale_or_degraded(snapshot.freshness_label, snapshot.data_quality_label):
            item_type = (
                DailyBriefItemType.STALE_DATA
                if snapshot.freshness_label != "fresh"
                else DailyBriefItemType.DATA_QUALITY_ISSUE
            )
            items.append(
                DailyBriefDraftItem(
                    item_type=item_type,
                    priority=DailyBriefPriority.HIGH
                    if snapshot.freshness_label in {"stale", "no_data"}
                    else DailyBriefPriority.NORMAL,
                    title=validate_daily_brief_text(f"{context.symbol.symbol} data freshness"),
                    summary=validate_daily_brief_text(
                        f"{context.symbol.symbol} latest data state is "
                        f"{safe_label(snapshot.freshness_label)} for {snapshot.timeframe}."
                    ),
                    reason=validate_daily_brief_text(
                        f"Market memory quality label is {safe_label(snapshot.data_quality_label)}."
                    ),
                    tags=["data_freshness", snapshot.freshness_label, snapshot.data_quality_label],
                    metadata=memory_metadata(context),
                    symbol_id=snapshot.symbol_id,
                    signal_id=snapshot.latest_signal_id,
                    analysis_run_id=snapshot.latest_analysis_run_id,
                    outcome_id=snapshot.latest_outcome_id,
                    source_type="market_memory",
                    source_id=snapshot.id,
                )
            )
    for context in provider_health:
        if is_provider_stale_or_degraded(context):
            symbol = context.symbol or "Workspace context"
            items.append(
                DailyBriefDraftItem(
                    item_type=DailyBriefItemType.STALE_DATA,
                    priority=priority_from_label(context.status),
                    title=validate_daily_brief_text(f"{symbol} provider freshness"),
                    summary=validate_daily_brief_text(
                        f"{symbol} provider freshness is {safe_label(context.freshness_label)}."
                    ),
                    reason=validate_daily_brief_text(context.summary),
                    tags=["provider_health", context.status, context.freshness_label],
                    metadata=provider_metadata(context),
                    symbol_id=context.symbol_id,
                    source_type="provider_health",
                    source_id=context.snapshot_id,
                )
            )
    for context in data_quality:
        run = context.run
        if run.quality_label in {"degraded", "poor", "insufficient_data"}:
            symbol = context.symbol.symbol if context.symbol is not None else "Workspace context"
            items.append(
                DailyBriefDraftItem(
                    item_type=DailyBriefItemType.DATA_QUALITY_ISSUE,
                    priority=priority_from_label(run.quality_label),
                    title=validate_daily_brief_text(f"{symbol} data quality issue"),
                    summary=validate_daily_brief_text(
                        f"{symbol} data quality is {safe_label(run.quality_label)}."
                    ),
                    reason=validate_daily_brief_text(
                        f"{run.finding_count} data-quality findings are available for review."
                    ),
                    tags=["data_quality", run.quality_label, run.scope_type],
                    metadata={
                        "qualityLabel": run.quality_label,
                        "qualityScore": run.quality_score,
                        "findingCount": run.finding_count,
                        "scopeType": run.scope_type,
                        "timeframe": run.timeframe,
                    },
                    symbol_id=run.symbol_id,
                    source_type="data_quality",
                    source_id=run.id,
                )
            )
    for context in latest_candles[:20]:
        items.append(
            DailyBriefDraftItem(
                item_type=DailyBriefItemType.WATCH_NEXT,
                priority=DailyBriefPriority.LOW,
                title=validate_daily_brief_text(
                    f"{context.symbol or 'Symbol'} latest final candle"
                ),
                summary=validate_daily_brief_text(
                    f"{context.symbol or 'Symbol'} has latest final candle data "
                    f"for {context.timeframe}."
                ),
                reason=validate_daily_brief_text(
                    "Inspect data freshness before relying on current context."
                ),
                tags=["latest_final_candle", context.timeframe],
                metadata={
                    "latestFinalCandleTime": context.latest_final_candle_time,
                    "timeframe": context.timeframe,
                },
                symbol_id=context.symbol_id,
                source_type="candle",
            )
        )
    return items


def build_outcome_items(
    outcomes: list[DailyBriefOutcomeContext],
    limit: int,
) -> list[DailyBriefDraftItem]:
    items: list[DailyBriefDraftItem] = []
    for context in outcomes[:limit]:
        outcome = context.outcome
        label = safe_outcome_label(outcome.outcome_label)
        items.append(
            DailyBriefDraftItem(
                item_type=DailyBriefItemType.OUTCOME_UPDATE,
                priority=DailyBriefPriority.NORMAL,
                title=validate_daily_brief_text(f"{context.symbol.symbol} outcome update"),
                summary=validate_daily_brief_text(
                    f"{context.symbol.symbol} has {label} over "
                    f"{outcome.horizon_minutes} minute horizon."
                ),
                reason=validate_daily_brief_text(
                    "Outcome became available from persisted final-candle evaluation."
                ),
                tags=["outcome_update", outcome.outcome_label, outcome.timeframe],
                metadata={
                    "outcomeLabel": outcome.outcome_label,
                    "evaluationStatus": outcome.evaluation_status,
                    "horizonMinutes": outcome.horizon_minutes,
                    "timeframe": outcome.timeframe,
                    "futureCandleCount": outcome.future_candle_count,
                    "directionFollowed": outcome.direction_followed,
                    "reversalDetected": outcome.reversal_detected,
                },
                symbol_id=outcome.symbol_id,
                signal_id=outcome.signal_id,
                analysis_run_id=outcome.analysis_run_id,
                outcome_id=outcome.id,
                source_type="signal_outcome",
                source_id=outcome.id,
            )
        )
    return items


def build_watch_next_items(
    signals: list[DailyBriefSignalContext],
    memory_contexts: list[DailyBriefMemoryContext],
    journal_contexts: list[DailyBriefJournalContext],
) -> list[DailyBriefDraftItem]:
    items: list[DailyBriefDraftItem] = []
    for context in signals[:30]:
        setup = context.setup_context
        if setup is not None and (setup.next_observations_json or setup.observation_zones_json):
            observations = setup.next_observations_json or setup.observation_zones_json
            for index, observation in enumerate(observations[:2]):
                items.append(
                    DailyBriefDraftItem(
                        item_type=DailyBriefItemType.WATCH_NEXT,
                        priority=DailyBriefPriority.LOW,
                        title=validate_daily_brief_text(f"{context.symbol.symbol} watch next"),
                        summary=context_message(observation, "Watch next setup context."),
                        reason=validate_daily_brief_text(
                            "Setup context lists a backend-safe next observation."
                        ),
                        tags=["watch_next", context.signal.timeframe],
                        metadata={"observation": observation, "index": index},
                        symbol_id=context.signal.symbol_id,
                        signal_id=context.signal.id,
                        analysis_run_id=context.signal.analysis_run_id,
                        setup_context_id=setup.id,
                        source_type="setup_context",
                        source_id=setup.id,
                    )
                )
        elif context.signal.classification_status == "signal":
            items.append(
                DailyBriefDraftItem(
                    item_type=DailyBriefItemType.WATCH_NEXT,
                    priority=DailyBriefPriority.LOW,
                    title=validate_daily_brief_text(f"{context.symbol.symbol} watch next"),
                    summary=validate_daily_brief_text(
                        "Monitor final candle close and review evidence."
                    ),
                    reason=validate_daily_brief_text(
                        "Directional context exists without a persisted next observation."
                    ),
                    tags=["watch_next", context.signal.timeframe],
                    metadata=signal_metadata(context),
                    symbol_id=context.signal.symbol_id,
                    signal_id=context.signal.id,
                    analysis_run_id=context.signal.analysis_run_id,
                    setup_context_id=setup.id if setup is not None else None,
                    source_type="signal",
                    source_id=context.signal.id,
                )
            )
    for context in memory_contexts[:20]:
        if context.snapshot.freshness_label != "fresh":
            items.append(
                DailyBriefDraftItem(
                    item_type=DailyBriefItemType.WATCH_NEXT,
                    priority=DailyBriefPriority.LOW,
                    title=validate_daily_brief_text(f"{context.symbol.symbol} freshness watch"),
                    summary=validate_daily_brief_text(
                        "Inspect data freshness before reviewing setup context."
                    ),
                    reason=validate_daily_brief_text(
                        f"Freshness label is {safe_label(context.snapshot.freshness_label)}."
                    ),
                    tags=["watch_next", "data_freshness", context.snapshot.timeframe],
                    metadata=memory_metadata(context),
                    symbol_id=context.snapshot.symbol_id,
                    signal_id=context.snapshot.latest_signal_id,
                    analysis_run_id=context.snapshot.latest_analysis_run_id,
                    source_type="market_memory",
                    source_id=context.snapshot.id,
                )
            )
    for context in journal_contexts[:10]:
        entry = context.entry
        symbol = context.symbol.symbol if context.symbol is not None else "Workspace context"
        items.append(
            DailyBriefDraftItem(
                item_type=DailyBriefItemType.JOURNAL_FOLLOW_UP,
                priority=DailyBriefPriority.LOW,
                title=validate_daily_brief_text(f"{symbol} journal follow-up"),
                summary=validate_daily_brief_text(entry.title),
                reason=validate_daily_brief_text(
                    "Recent journal entry is available for follow-up review."
                ),
                tags=["journal_follow_up", entry.decision_type],
                metadata={
                    "decisionType": entry.decision_type,
                    "status": entry.status,
                    "userBias": entry.user_bias,
                    "tags": entry.tags_json,
                },
                symbol_id=context.signal.symbol_id if context.signal is not None else None,
                signal_id=entry.signal_id,
                analysis_run_id=entry.analysis_run_id,
                setup_context_id=entry.setup_context_id,
                source_type="journal_entry",
                source_id=entry.id,
            )
        )
    return items


def build_pending_action_items(
    pending_actions: list[DailyBriefActionContext],
    due_scans: list[DailyBriefScanContext],
    limit: int,
) -> list[DailyBriefDraftItem]:
    items: list[DailyBriefDraftItem] = []
    for context in pending_actions[:limit]:
        action = context.action_item
        symbol = context.symbol.symbol if context.symbol is not None else "Workspace context"
        items.append(
            DailyBriefDraftItem(
                item_type=DailyBriefItemType.PENDING_ACTION,
                priority=priority_from_label(action.priority if action.status != "due" else "high"),
                title=validate_daily_brief_text(f"{symbol} backend action due"),
                summary=validate_daily_brief_text(
                    f"Backend-safe action due: {safe_action_label(action.action_type)}."
                ),
                reason=validate_daily_brief_text(
                    "Brief generation lists this action only and does not execute it."
                ),
                tags=["pending_action", action.action_type, action.status],
                metadata={
                    "actionType": action.action_type,
                    "status": action.status,
                    "priority": action.priority,
                    "dueAt": action.due_at,
                    "horizonMinutes": action.horizon_minutes,
                },
                symbol_id=context.signal.symbol_id if context.signal is not None else None,
                signal_id=action.signal_id,
                analysis_run_id=action.analysis_run_id,
                action_item_id=action.id,
                source_type="reasoning_action_item",
                source_id=action.id,
            )
        )
    for context in due_scans[:limit]:
        config = context.scan_config
        label = (
            context.symbol.symbol
            if context.symbol is not None
            else context.watchlist.name
            if context.watchlist is not None
            else "Watchlist"
        )
        items.append(
            DailyBriefDraftItem(
                item_type=DailyBriefItemType.PENDING_ACTION,
                priority=DailyBriefPriority.NORMAL,
                title=validate_daily_brief_text(f"{label} scheduled scan due"),
                summary=validate_daily_brief_text("Scheduled backend scan is due."),
                reason=validate_daily_brief_text(
                    "Brief generation lists the due scan and does not run it."
                ),
                tags=["pending_action", "scheduled_scan", config.scan_mode],
                metadata={
                    "scanConfigId": config.id,
                    "scanMode": config.scan_mode,
                    "nextRunAt": config.next_run_at,
                    "timeframe": config.timeframe,
                },
                symbol_id=config.symbol_id,
                source_type="scheduled_scan_config",
                source_id=config.id,
            )
        )
    return items


def build_market_context_items(
    market_contexts: list[DailyBriefMarketContext],
) -> list[DailyBriefDraftItem]:
    items: list[DailyBriefDraftItem] = []
    for context in market_contexts:
        symbol = context.symbol or "Workspace context"
        items.append(
            DailyBriefDraftItem(
                item_type=DailyBriefItemType.MARKET_CONTEXT,
                priority=market_context_priority(context),
                title=validate_daily_brief_text(f"{symbol} {safe_label(context.source_type)}"),
                summary=validate_daily_brief_text(context.summary),
                reason=validate_daily_brief_text(
                    f"Persisted {safe_label(context.source_type)} matters "
                    "for today's review context."
                ),
                tags=["market_context", context.source_type, context.label],
                metadata=context.metadata,
                symbol_id=context.symbol_id,
                signal_id=context.signal_id,
                analysis_run_id=context.analysis_run_id,
                source_type=context.source_type,
                source_id=context.source_id,
            )
        )
    return items


def build_sections(
    items: list[DailyBriefDraftItem],
    artifacts: DailyBriefArtifacts,
) -> dict[str, object]:
    sections: dict[str, object] = {name: [] for name in SECTION_NAMES}
    for item in items:
        section_name = SECTION_BY_ITEM_TYPE[item.item_type]
        sections[section_name].append(item_to_section_json(item))
    sections["digest_context"] = (
        {
            "id": str(artifacts.digest_context.digest.id),
            "type": artifacts.digest_context.digest.digest_type,
            "title": artifacts.digest_context.digest.title,
            "itemCount": len(artifacts.digest_context.items),
        }
        if artifacts.digest_context is not None
        else None
    )
    return to_json_value(sections)


def item_to_section_json(item: DailyBriefDraftItem) -> dict[str, object]:
    return {
        "itemType": item.item_type.value,
        "priority": item.priority.value,
        "title": item.title,
        "summary": item.summary,
        "reason": item.reason,
        "symbolId": item.symbol_id,
        "signalId": item.signal_id,
        "analysisRunId": item.analysis_run_id,
        "outcomeId": item.outcome_id,
        "actionItemId": item.action_item_id,
        "setupContextId": item.setup_context_id,
        "sourceType": item.source_type,
        "sourceId": item.source_id,
        "tags": item.tags,
        "metadata": item.metadata,
    }


def build_warnings(
    artifacts: DailyBriefArtifacts,
    raw_item_count: int,
    max_items: int,
) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    if raw_item_count > max_items:
        warnings.append(
            {
                "code": "daily_brief_item_limit_applied",
                "severity": "low",
                "message": "Daily brief items were capped by the configured limit",
            }
        )
    if (
        not artifacts.priority_signals
        and not artifacts.recent_signals
        and not artifacts.memory_contexts
    ):
        warnings.append(
            {
                "code": "daily_brief_empty_artifacts",
                "severity": "medium",
                "message": "No recent signal or market memory artifacts matched the request",
            }
        )
    if artifacts.digest_context is None:
        warnings.append(
            {
                "code": "signal_digest_unavailable",
                "severity": "low",
                "message": "No matching persisted signal digest was available",
            }
        )
    return warnings


def merge_signal_contexts(
    priority_signals: list[DailyBriefSignalContext],
    recent_signals: list[DailyBriefSignalContext],
) -> list[DailyBriefSignalContext]:
    merged: list[DailyBriefSignalContext] = []
    seen: set[UUID] = set()
    for context in [*priority_signals, *recent_signals]:
        if context.signal.id not in seen:
            seen.add(context.signal.id)
            merged.append(context)
    return merged


def unique_items(items: list[DailyBriefDraftItem]) -> list[DailyBriefDraftItem]:
    unique: list[DailyBriefDraftItem] = []
    seen: set[tuple[str, UUID | None, UUID | None, str]] = set()
    for item in items:
        key = (item.item_type.value, item.signal_id, item.symbol_id, item.title)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def count_item_type(items: list[DailyBriefDraftItem], item_type: DailyBriefItemType) -> int:
    return sum(1 for item in items if item.item_type == item_type)


def is_stale_or_degraded(freshness_label: str | None, data_quality_label: str | None) -> bool:
    return (freshness_label or "unknown") != "fresh" or (data_quality_label or "unknown") in {
        "degraded",
        "poor",
        "insufficient",
        "insufficient_data",
        "unknown",
        "weak",
    }


def is_provider_stale_or_degraded(context: DailyBriefProviderHealthContext) -> bool:
    return (
        context.status in {"degraded", "stale", "failing", "unavailable", "unknown"}
        or context.freshness_label != "fresh"
    )


def has_conflict_context(*values: str | None) -> bool:
    tokens = ("conflict", "fakeout", "chop", "range", "sideways")
    return any(
        value is not None and any(token in value.lower() for token in tokens) for value in values
    )


def review_reason(context: DailyBriefSignalContext) -> str:
    if context.priority_score is not None and context.priority_score.reasons_json:
        return context_message(
            context.priority_score.reasons_json[0], "Review priority score ranked this setup first."
        )
    if context.setup_context is not None:
        return validate_daily_brief_text(context.setup_context.summary)
    return validate_daily_brief_text(context.signal.summary)


def confirmation_reason(context: DailyBriefSignalContext) -> str:
    setup = context.setup_context
    readiness = context.readiness
    if setup is not None and setup.wait_conditions_json:
        return context_message(
            setup.wait_conditions_json[0], "Wait condition requires confirmation."
        )
    if setup is not None and setup.timeframe_agreement_json:
        return context_message(
            setup.timeframe_agreement_json, "Mixed timeframe context needs confirmation."
        )
    if readiness is not None and readiness.warnings_json:
        return context_message(readiness.warnings_json[0], "Decision readiness needs confirmation.")
    if context.priority_score is not None and context.priority_score.warnings_json:
        return context_message(
            context.priority_score.warnings_json[0], "Priority score includes confirmation warning."
        )
    return validate_daily_brief_text("Medium confidence or mixed context requires confirmation.")


def avoid_reason(context: DailyBriefSignalContext) -> str:
    setup = context.setup_context
    if setup is not None and setup.avoid_reasons_json:
        return context_message(
            setup.avoid_reasons_json[0], "Setup context marks an avoid condition."
        )
    if context.signal.no_signal_reason:
        return safe_label(context.signal.no_signal_reason)
    if context.priority_score is not None and context.priority_score.penalties_json:
        return context_message(
            context.priority_score.penalties_json[0], "Priority score includes avoid condition."
        )
    return validate_daily_brief_text(
        "No directional signal, low quality, stale data, or conflicting evidence."
    )


def signal_metadata(context: DailyBriefSignalContext) -> dict[str, object]:
    signal = context.signal
    return {
        "symbol": context.symbol.symbol,
        "bias": signal.bias,
        "classificationStatus": signal.classification_status,
        "confidenceScore": signal.confidence_score,
        "confidenceLabel": signal.confidence_label,
        "timeframe": signal.timeframe,
        "patternType": signal.pattern_type,
        "noSignalReason": signal.no_signal_reason,
        "createdAt": signal.created_at,
        "evidenceCount": context.evidence_count,
        "riskCount": context.risk_count,
        "priorityScore": context.priority_score.priority_score
        if context.priority_score is not None
        else None,
        "priorityLabel": context.priority_score.priority_label
        if context.priority_score is not None
        else None,
        "reviewBucket": context.priority_score.review_bucket
        if context.priority_score is not None
        else None,
        "setupQualityLabel": context.setup_context.setup_quality_label
        if context.setup_context is not None
        else None,
        "readinessLabel": context.readiness.readiness_label
        if context.readiness is not None
        else None,
        "freshnessLabel": context.memory.freshness_label if context.memory is not None else None,
    }


def memory_metadata(context: DailyBriefMemoryContext) -> dict[str, object]:
    snapshot = context.snapshot
    return {
        "symbol": context.symbol.symbol,
        "timeframe": snapshot.timeframe,
        "freshnessLabel": snapshot.freshness_label,
        "dataQualityLabel": snapshot.data_quality_label,
        "latestFinalCandleTime": snapshot.latest_final_candle_time,
        "marketRegimeLabel": snapshot.market_regime_label,
        "marketSessionLabel": snapshot.market_session_label,
        "multiTimeframeLabel": snapshot.multi_timeframe_label,
        "crossAssetLabel": snapshot.cross_asset_label,
        "warnings": snapshot.warnings_json,
    }


def provider_metadata(context: DailyBriefProviderHealthContext) -> dict[str, object]:
    return {
        "status": context.status,
        "freshnessLabel": context.freshness_label,
        "latestFinalCandleTime": context.latest_final_candle_time,
        "missingCandleCount": context.missing_candle_count,
        "staleSeconds": context.stale_seconds,
        "provider": context.provider,
        "timeframe": context.timeframe,
        "sourceId": context.source_id,
    }


def market_context_priority(context: DailyBriefMarketContext) -> DailyBriefPriority:
    label = safe_label(context.label)
    if label in {
        "conflicting",
        "divergent",
        "fakeout risk",
        "spike",
        "degraded",
        "insufficient data",
    }:
        return DailyBriefPriority.HIGH
    if label in {"mixed", "partially aligned", "review recommended"}:
        return DailyBriefPriority.NORMAL
    return DailyBriefPriority.LOW
