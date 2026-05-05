import type {
  ActionItem,
  ApiFailure,
  DecisionReadinessAssessmentResponse,
  MarketMemorySnapshot,
  SetupContext,
  SignalClassification,
  SignalDigestItem,
  SignalDigestRun,
  SignalOutcome,
  SymbolRead,
  UUID,
  Watchlist,
  WatchlistItem,
  Workspace,
} from "@/lib/api/types";
import type { DecisionReadinessAssessmentRead } from "@/lib/api/readiness";
import type { OperatorReviewItem } from "@/lib/api/reviews";
import { humanizeLabel, shortIdentifier } from "@/lib/formatting/labels";
import {
  contextText,
  outcomeObservationLabel,
  readString,
  safeBriefText,
  safeHumanLabel,
} from "./labels";
import type {
  BriefActiveSetupItem,
  BriefAvoidConditionItem,
  BriefDataQualityIssue,
  BriefDigestSummary,
  BriefFailure,
  BriefMarketFocusItem,
  BriefOutcomeUpdateItem,
  BriefPendingActionItem,
  BriefReviewNeededItem,
  BriefSectionStatus,
  BriefWatchNextItem,
  WorkspaceBrief,
} from "./types";

export type BriefSignalBundle = {
  signal: SignalClassification;
  setupContext: SetupContext | null;
  outcomes: SignalOutcome[];
  readiness: DecisionReadinessAssessmentResponse | null;
};

export type BriefWatchlistWithItems = {
  watchlist: Watchlist;
  items: WatchlistItem[];
};

export type ComposeBriefInput = {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: UUID | null;
  workspace: Workspace | null;
  symbols: SymbolRead[];
  watchlists: BriefWatchlistWithItems[];
  memorySnapshots: MarketMemorySnapshot[];
  signalBundles: BriefSignalBundle[];
  dueActionItems: ActionItem[];
  readinessAssessments: DecisionReadinessAssessmentRead[];
  operatorReviews: OperatorReviewItem[];
  signalDigests: SignalDigestRun[];
  latestDigestItems: SignalDigestItem[];
  failures: BriefFailure[];
  backendUnavailable: boolean;
  generatedAt: string;
};

const maxMarketFocusItems = 8;
const maxSetupItems = 8;
const maxOutcomeItems = 8;
const maxPendingActions = 8;
const maxWatchNextItems = 8;
const maxReviewItems = 8;
const maxDigestItems = 6;

export function composeBrief(input: ComposeBriefInput): WorkspaceBrief {
  const symbolMap = new Map(input.symbols.map((symbol) => [symbol.id, symbol]));
  const bundleMap = new Map(input.signalBundles.map((bundle) => [bundle.signal.signal.id, bundle]));
  const marketFocus = buildMarketFocus(input.memorySnapshots, symbolMap, bundleMap);
  const activeSetups = buildActiveSetups(input.signalBundles, symbolMap);
  const avoidConditions = buildAvoidConditions(input.memorySnapshots, input.signalBundles, input.readinessAssessments, symbolMap);
  const outcomeUpdates = buildOutcomeUpdates(input.signalBundles, symbolMap);
  const pendingActions = buildPendingActions(input.dueActionItems);
  const dataQualityIssues = buildDataQualityIssues(input.memorySnapshots, input.signalBundles, symbolMap);
  const watchNext = buildWatchNext(input.signalBundles, symbolMap);
  const reviewNeeded = buildReviewNeeded(input.operatorReviews, input.readinessAssessments);
  const digestSummaries = buildDigestSummaries(input.latestDigestItems);
  const reviewRecommendedCount = avoidConditions.length + reviewNeeded.length + dataQualityIssues.length;

  return {
    appName: input.appName,
    apiBaseUrl: input.apiBaseUrl,
    workspace: input.workspace ? { id: input.workspace.id, name: input.workspace.name } : null,
    requestedWorkspaceId: input.requestedWorkspaceId,
    generatedAt: input.generatedAt,
    periodStart: null,
    periodEnd: null,
    timezone: null,
    watchlistId: input.watchlists[0]?.watchlist.id || null,
    sourceLabel: "Frontend fallback composition",
    backendUnavailable: input.backendUnavailable,
    summary: {
      totalSymbolsReviewed: marketFocus.length,
      freshSymbols: input.memorySnapshots.filter((snapshot) => snapshot.freshness_label === "fresh").length,
      staleOrDegradedSymbols: input.memorySnapshots.filter(isStaleOrDegraded).length,
      activeSetupCount: activeSetups.length,
      reviewRecommendedCount,
      recentOutcomeUpdateCount: outcomeUpdates.length,
      pendingBackendActionCount: pendingActions.length,
    },
    marketFocus,
    activeSetups,
    avoidConditions,
    outcomeUpdates,
    pendingActions,
    dataQualityIssues,
    watchNext,
    reviewNeeded,
    digestSummaries,
    sectionStatuses: {
      workspace: sectionStatus("Workspace", Boolean(input.workspace), input.failures, ["Workspaces"]),
      marketFocus: sectionStatus("Market focus", marketFocus.length > 0, input.failures, ["Market memory", "Symbols", "Watchlists"]),
      activeSetups: sectionStatus("Active setups", activeSetups.length > 0, input.failures, ["Signals", "Setup context"]),
      avoidConditions: sectionStatus("Avoid conditions", avoidConditions.length > 0, input.failures, ["Market memory", "Setup context", "Decision readiness"]),
      outcomeUpdates: sectionStatus("Outcome updates", outcomeUpdates.length > 0, input.failures, ["Signal outcomes"]),
      pendingActions: sectionStatus("Pending actions", pendingActions.length > 0, input.failures, ["Backend action items"]),
      dataQuality: sectionStatus("Data quality", dataQualityIssues.length > 0, input.failures, ["Market memory", "Setup context"]),
      watchNext: sectionStatus("Watch next", watchNext.length > 0, input.failures, ["Setup context"]),
      reviewNeeded: sectionStatus("Review needed", reviewNeeded.length > 0, input.failures, ["Operator reviews", "Decision readiness"]),
      digests: sectionStatus("Digest summaries", digestSummaries.length > 0, input.failures, ["Signal digests", "Signal digest items"]),
    },
    failures: input.failures,
  };
}

export function toBriefFailure(label: string, result: ApiFailure): BriefFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}

function buildMarketFocus(
  memorySnapshots: MarketMemorySnapshot[],
  symbolMap: Map<UUID, SymbolRead>,
  bundleMap: Map<UUID, BriefSignalBundle>,
): BriefMarketFocusItem[] {
  return memorySnapshots
    .slice()
    .sort(compareMemoryFocus)
    .slice(0, maxMarketFocusItems)
    .map((snapshot) => {
      const symbol = symbolMap.get(snapshot.symbol_id);
      const bundle = snapshot.latest_signal_id ? bundleMap.get(snapshot.latest_signal_id) : null;
      return {
        id: snapshot.id,
        symbolId: snapshot.symbol_id,
        symbol: symbol?.symbol || shortIdentifier(snapshot.symbol_id),
        displayName: symbol?.display_name || "Symbol metadata unavailable",
        timeframe: snapshot.timeframe,
        latestBias: normalizeBias(snapshot.latest_signal_bias),
        confidenceLabel: snapshot.latest_signal_confidence_label || "Not scored",
        freshnessLabel: snapshot.freshness_label,
        dataQualityLabel: snapshot.data_quality_label,
        marketRegimeLabel: snapshot.market_regime_label || "Not available",
        marketSessionLabel: snapshot.market_session_label || "Not available",
        setupQualityLabel: bundle?.setupContext?.setup_quality_label || "Not available",
        topWarning: topWarning(snapshot.warnings_json) || "No current warning",
        signalId: snapshot.latest_signal_id,
      };
    });
}

function buildActiveSetups(
  signalBundles: BriefSignalBundle[],
  symbolMap: Map<UUID, SymbolRead>,
): BriefActiveSetupItem[] {
  return signalBundles
    .filter(({ signal }) => isDirectionalBias(signal.signal.bias))
    .slice(0, maxSetupItems)
    .map(({ signal, setupContext }) => ({
      signalId: signal.signal.id,
      symbolId: signal.signal.symbol_id,
      symbol: symbolMap.get(signal.signal.symbol_id)?.symbol || shortIdentifier(signal.signal.symbol_id),
      timeframe: signal.signal.timeframe,
      bias: normalizeBias(setupContext?.directional_bias || signal.signal.bias),
      patternType: signal.signal.pattern_type || "No pattern",
      confidenceLabel: signal.signal.confidence_label,
      setupQualityLabel: setupContext?.setup_quality_label || "Not available",
      keyEvidence: signal.evidence.slice(0, 3).map((item) => safeBriefText(item.message, "Evidence context")),
      invalidationContext: setupContext?.invalidation_context_json.length
        ? contextText(setupContext.invalidation_context_json[0], "Invalidation context")
        : null,
      waitCondition: setupContext?.wait_conditions_json.length
        ? contextText(setupContext.wait_conditions_json[0], "Wait condition")
        : null,
      reviewLink: `/signals/${signal.signal.id}`,
    }));
}

function buildAvoidConditions(
  memorySnapshots: MarketMemorySnapshot[],
  signalBundles: BriefSignalBundle[],
  readinessAssessments: DecisionReadinessAssessmentRead[],
  symbolMap: Map<UUID, SymbolRead>,
): BriefAvoidConditionItem[] {
  const items: BriefAvoidConditionItem[] = [];
  for (const snapshot of memorySnapshots) {
    const symbol = symbolMap.get(snapshot.symbol_id)?.symbol || shortIdentifier(snapshot.symbol_id);
    if (snapshot.freshness_label !== "fresh") {
      items.push({
        id: `${snapshot.id}:freshness`,
        symbolId: snapshot.symbol_id,
        symbol,
        timeframe: snapshot.timeframe,
        condition: "Stale data",
        reason: `${safeHumanLabel(snapshot.freshness_label)} freshness state`,
        severity: "medium",
        source: "Market memory",
        signalId: snapshot.latest_signal_id,
      });
    }
    if (!isDirectionalBias(snapshot.latest_signal_bias)) {
      items.push({
        id: `${snapshot.id}:bias`,
        symbolId: snapshot.symbol_id,
        symbol,
        timeframe: snapshot.timeframe,
        condition: "No directional signal",
        reason: "Latest memory snapshot did not expose a directional bias.",
        severity: "low",
        source: "Market memory",
        signalId: snapshot.latest_signal_id,
      });
    }
    if (snapshot.data_quality_label === "weak" || snapshot.data_quality_label === "degraded") {
      items.push({
        id: `${snapshot.id}:quality`,
        symbolId: snapshot.symbol_id,
        symbol,
        timeframe: snapshot.timeframe,
        condition: "Low data quality",
        reason: `${safeHumanLabel(snapshot.data_quality_label)} data quality state`,
        severity: "medium",
        source: "Market memory",
        signalId: snapshot.latest_signal_id,
      });
    }
    for (const warning of snapshot.warnings_json.slice(0, 2)) {
      items.push({
        id: `${snapshot.id}:warning:${items.length}`,
        symbolId: snapshot.symbol_id,
        symbol,
        timeframe: snapshot.timeframe,
        condition: warningCondition(warning),
        reason: contextText(warning, "Review recommended"),
        severity: readString(warning, "severity") || "medium",
        source: "Market memory",
        signalId: snapshot.latest_signal_id,
      });
    }
  }
  for (const { signal, setupContext } of signalBundles) {
    if (!setupContext) {
      continue;
    }
    const symbol = symbolMap.get(signal.signal.symbol_id)?.symbol || shortIdentifier(signal.signal.symbol_id);
    for (const reason of setupContext.avoid_reasons_json.slice(0, 3)) {
      items.push({
        id: `${setupContext.id}:avoid:${items.length}`,
        symbolId: signal.signal.symbol_id,
        symbol,
        timeframe: signal.signal.timeframe,
        condition: warningCondition(reason),
        reason: contextText(reason, "Avoid condition"),
        severity: readString(reason, "severity") || "medium",
        source: "Setup context",
        signalId: signal.signal.id,
      });
    }
  }
  for (const assessment of readinessAssessments.slice(0, 12)) {
    if (assessment.readiness_label === "ready" && assessment.blockers_json.length === 0) {
      continue;
    }
    const reason = assessment.blockers_json[0] || assessment.warnings_json[0] || null;
    items.push({
      id: `${assessment.id}:readiness`,
      symbolId: null,
      symbol: "Workspace",
      timeframe: null,
      condition: "Unresolved review needed",
      reason: reason ? contextText(reason, assessment.summary) : safeBriefText(assessment.summary),
      severity: assessment.blockers_json.length ? "high" : "medium",
      source: "Decision readiness",
      signalId: assessment.signal_id,
    });
  }
  return uniqueBy(items, (item) => `${item.symbolId}:${item.timeframe}:${item.condition}:${item.reason}`).slice(0, 12);
}

function buildOutcomeUpdates(
  signalBundles: BriefSignalBundle[],
  symbolMap: Map<UUID, SymbolRead>,
): BriefOutcomeUpdateItem[] {
  return signalBundles
    .flatMap(({ signal, outcomes }) =>
      outcomes.map((outcome) => ({
        id: outcome.id,
        signalId: signal.signal.id,
        symbolId: signal.signal.symbol_id,
        symbol: symbolMap.get(signal.signal.symbol_id)?.symbol || shortIdentifier(signal.signal.symbol_id),
        timeframe: signal.signal.timeframe,
        horizon: `${outcome.horizon_minutes} min`,
        outcomeLabel: outcome.outcome_label,
        observationLabel: outcomeObservationLabel(outcome.direction_followed, outcome.reversal_detected),
        safeSummary: safeBriefText(
          `${humanizeLabel(outcome.outcome_label)} over ${outcome.horizon_minutes} minute horizon.`,
          "Outcome update available.",
        ),
      })),
    )
    .slice(0, maxOutcomeItems);
}

function buildPendingActions(actionItems: ActionItem[]): BriefPendingActionItem[] {
  return actionItems.slice(0, maxPendingActions).map((item) => ({
    id: item.id,
    actionType: item.action_type,
    status: item.status,
    dueTime: item.due_at,
    source: item.source_scenario_id ? "Reasoning scenario" : "Backend action plan",
    safeLabel: safeBriefText(item.title || item.description, safeHumanLabel(item.action_type)),
  }));
}

function buildDataQualityIssues(
  memorySnapshots: MarketMemorySnapshot[],
  signalBundles: BriefSignalBundle[],
  symbolMap: Map<UUID, SymbolRead>,
): BriefDataQualityIssue[] {
  const items: BriefDataQualityIssue[] = [];
  for (const snapshot of memorySnapshots) {
    const symbol = symbolMap.get(snapshot.symbol_id)?.symbol || shortIdentifier(snapshot.symbol_id);
    if (isStaleOrDegraded(snapshot)) {
      items.push({
        id: `${snapshot.id}:memory-quality`,
        symbolId: snapshot.symbol_id,
        symbol,
        timeframe: snapshot.timeframe,
        label: snapshot.data_quality_label === "fresh" ? snapshot.freshness_label : snapshot.data_quality_label,
        detail: `${safeHumanLabel(snapshot.freshness_label)} freshness and ${safeHumanLabel(snapshot.data_quality_label)} quality.`,
        severity: snapshot.data_quality_label === "weak" ? "high" : "medium",
        source: "Market memory",
      });
    }
    for (const warning of snapshot.warnings_json.slice(0, 2)) {
      items.push({
        id: `${snapshot.id}:memory-warning:${items.length}`,
        symbolId: snapshot.symbol_id,
        symbol,
        timeframe: snapshot.timeframe,
        label: readString(warning, "code") || "Data quality issue",
        detail: contextText(warning, "Data quality issue"),
        severity: readString(warning, "severity") || "medium",
        source: "Market memory",
      });
    }
  }
  for (const { signal, setupContext } of signalBundles) {
    if (!setupContext) {
      continue;
    }
    const symbol = symbolMap.get(signal.signal.symbol_id)?.symbol || shortIdentifier(signal.signal.symbol_id);
    for (const warning of setupContext.data_quality_warnings_json.slice(0, 3)) {
      items.push({
        id: `${setupContext.id}:setup-quality:${items.length}`,
        symbolId: signal.signal.symbol_id,
        symbol,
        timeframe: signal.signal.timeframe,
        label: readString(warning, "code") || "Data quality warning",
        detail: contextText(warning, "Data quality warning"),
        severity: readString(warning, "severity") || "medium",
        source: "Setup context",
      });
    }
  }
  return uniqueBy(items, (item) => `${item.symbolId}:${item.timeframe}:${item.label}:${item.detail}`).slice(0, 10);
}

function buildWatchNext(
  signalBundles: BriefSignalBundle[],
  symbolMap: Map<UUID, SymbolRead>,
): BriefWatchNextItem[] {
  return signalBundles
    .flatMap(({ signal, setupContext }) => {
      if (!setupContext) {
        return [];
      }
      const symbol = symbolMap.get(signal.signal.symbol_id)?.symbol || shortIdentifier(signal.signal.symbol_id);
      const nextObservations = setupContext.next_observations_json.length
        ? setupContext.next_observations_json
        : setupContext.observation_zones_json;
      return nextObservations.slice(0, 3).map((item, index) => ({
        id: `${setupContext.id}:next:${index}`,
        symbolId: signal.signal.symbol_id,
        symbol,
        timeframe: signal.signal.timeframe,
        observation: contextText(item, "Watch-next observation"),
        reason: readString(item, "reason") ? safeBriefText(readString(item, "reason")) : setupContext.summary || "Setup context",
        sourceArtifact: `Setup context ${shortIdentifier(setupContext.id)}`,
        signalId: signal.signal.id,
      }));
    })
    .slice(0, maxWatchNextItems);
}

function buildReviewNeeded(
  reviews: OperatorReviewItem[],
  readinessAssessments: DecisionReadinessAssessmentRead[],
): BriefReviewNeededItem[] {
  const openReviews = reviews.filter((review) => !["resolved", "dismissed", "closed"].includes(review.status));
  const reviewItems: BriefReviewNeededItem[] = openReviews.slice(0, maxReviewItems).map((review) => ({
    id: review.id,
    label: safeBriefText(review.title, "Review recommended"),
    reason: safeBriefText(review.summary, review.reason_code || "Review recommended"),
    priority: review.priority,
    source: safeHumanLabel(review.source_type),
    signalId: review.related_signal_id,
  }));
  const readinessItems: BriefReviewNeededItem[] = readinessAssessments
    .filter((assessment) => assessment.readiness_label !== "ready" || assessment.blockers_json.length > 0)
    .slice(0, maxReviewItems)
    .map((assessment) => ({
      id: assessment.id,
      label: safeHumanLabel(assessment.readiness_label, "Review recommended"),
      reason: safeBriefText(assessment.summary, "Decision readiness item"),
      priority: assessment.blockers_json.length ? "high" : "normal",
      source: "Decision readiness",
      signalId: assessment.signal_id,
    }));
  return uniqueBy([...reviewItems, ...readinessItems], (item) => `${item.source}:${item.signalId}:${item.label}`).slice(0, maxReviewItems);
}

function buildDigestSummaries(items: SignalDigestItem[]): BriefDigestSummary[] {
  return items.slice(0, maxDigestItems).map((item) => ({
    id: item.id,
    title: safeBriefText(item.title, "Digest item"),
    summary: safeBriefText(item.summary, "Digest context"),
    priority: item.priority,
    itemType: item.item_type,
    signalId: item.signal_id,
  }));
}

function compareMemoryFocus(left: MarketMemorySnapshot, right: MarketMemorySnapshot): number {
  const leftScore = focusScore(left);
  const rightScore = focusScore(right);
  if (leftScore !== rightScore) {
    return rightScore - leftScore;
  }
  return (right.updated_at || "").localeCompare(left.updated_at || "");
}

function focusScore(snapshot: MarketMemorySnapshot): number {
  let score = 0;
  if (snapshot.freshness_label === "fresh") {
    score += 5;
  }
  if (isDirectionalBias(snapshot.latest_signal_bias)) {
    score += 4;
  }
  if (snapshot.latest_signal_id) {
    score += 3;
  }
  if (snapshot.data_quality_label === "weak" || snapshot.warnings_json.length > 0) {
    score += 2;
  }
  return score;
}

function isDirectionalBias(value: string | null | undefined): boolean {
  const normalized = value?.toLowerCase();
  return normalized === "bullish" || normalized === "bearish";
}

function normalizeBias(value: string | null | undefined): string {
  if (isDirectionalBias(value)) {
    return `${value?.toLowerCase()} bias`;
  }
  if (value?.toLowerCase() === "neutral") {
    return "neutral";
  }
  return "no directional signal";
}

function isStaleOrDegraded(snapshot: MarketMemorySnapshot): boolean {
  return snapshot.freshness_label !== "fresh" || ["weak", "degraded"].includes(snapshot.data_quality_label);
}

function topWarning(warnings: MarketMemorySnapshot["warnings_json"]): string | null {
  return warnings.length ? contextText(warnings[0], "Review recommended") : null;
}

function warningCondition(value: Record<string, unknown>): string {
  const code = typeof value.code === "string" ? value.code.toLowerCase() : "";
  const message = typeof value.message === "string" ? value.message.toLowerCase() : "";
  const combined = `${code} ${message}`;
  if (combined.includes("conflict")) {
    return "Conflicting evidence";
  }
  if (combined.includes("fakeout") || combined.includes("chop") || combined.includes("range")) {
    return "Range or chop risk";
  }
  if (combined.includes("quality")) {
    return "Low data quality";
  }
  if (combined.includes("stale")) {
    return "Stale data";
  }
  return "Review recommended";
}

function sectionStatus(
  label: string,
  hasData: boolean,
  failures: BriefFailure[],
  sourceLabels: string[],
): BriefSectionStatus {
  const matchingFailure = failures.find((failure) =>
    sourceLabels.some((sourceLabel) => failure.label.toLowerCase().includes(sourceLabel.toLowerCase())),
  );
  if (matchingFailure) {
    return {
      state: "unavailable",
      label: `${label} unavailable`,
      message: matchingFailure.missing ? "The optional backend endpoint was not available." : matchingFailure.message,
    };
  }
  if (!hasData) {
    return {
      state: "empty",
      label: `${label} empty`,
      message: "No matching backend artifacts were returned.",
    };
  }
  return {
    state: "ready",
    label,
    message: "Section data loaded.",
  };
}

function uniqueBy<T>(items: T[], keyForItem: (item: T) => string): T[] {
  const seen = new Set<string>();
  const uniqueItems: T[] = [];
  for (const item of items) {
    const key = keyForItem(item);
    if (!seen.has(key)) {
      seen.add(key);
      uniqueItems.push(item);
    }
  }
  return uniqueItems;
}
