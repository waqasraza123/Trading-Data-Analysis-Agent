import { getPublicEnv } from "@/config/env";
import {
  composeBrief,
  toBriefFailure,
  type BriefSignalBundle,
  type BriefWatchlistWithItems,
} from "@/lib/brief/composeBrief";
import type {
  BriefActiveSetupItem,
  BriefAvoidConditionItem,
  BriefDataQualityIssue,
  BriefDigestSummary,
  BriefFailure,
  BriefOutcomeUpdateItem,
  BriefPendingActionItem,
  BriefReviewNeededItem,
  BriefSectionStatus,
  BriefWatchNextItem,
  WorkspaceBrief,
} from "@/lib/brief/types";
import { getLatestWorkspaceDailyBrief } from "./dailyBriefs";
import { listAnalysisRuns, listMarketMemorySnapshots, listSymbols, listWorkspaces } from "./market";
import { listSignalOutcomes } from "./outcomes";
import {
  getLatestSignalReadiness,
  listDecisionReadinessAssessments,
  type DecisionReadinessAssessmentListResponse,
} from "./readiness";
import { listOperatorReviewItems, type OperatorReviewItem } from "./reviews";
import { listSignalDigestItems, listSignalDigests } from "./signal-digests";
import { getAnalysisRunSignal, getSignal } from "./signals";
import { getSignalSetupContext } from "./setup-context";
import { getApiHealth, getWorkerStatus, listDueActionItems } from "./status";
import {
  listDueScheduledScanConfigs,
  listScheduledScanConfigs,
  listWatchlistItems,
  listWatchlists,
} from "./watchlists";
import type {
  ApiResult,
  JsonRecord,
  HealthResponse,
  ScheduledScanConfig,
  SignalDigestItem,
  SignalDigestRun,
  UUID,
  Watchlist,
  WatchlistItem,
  Workspace,
} from "./types";

export async function getWorkspaceBrief(params: { workspaceId?: string }): Promise<WorkspaceBrief> {
  const env = getPublicEnv();
  const failures: BriefFailure[] = [];
  const generatedAt = new Date().toISOString();
  const [workspacesResult, symbolsResult, healthResult, workerStatusResult] = await Promise.all([
    listWorkspaces(),
    listSymbols(),
    getApiHealth(),
    getWorkerStatus(),
  ]);
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const symbols = readResult("Symbols", symbolsResult, [], failures);
  readNullableResult("API health", healthResult, failures);
  readNullableResult("Worker status", workerStatusResult, failures);
  const workspace = workspaces.find((candidate) => candidate.id === params.workspaceId) || workspaces[0] || null;
  const backendUnavailable = isBackendUnavailable(healthResult, workspacesResult);

  if (!workspace) {
    return composeBrief({
      appName: env.appName,
      apiBaseUrl: env.apiBaseUrl,
      requestedWorkspaceId: params.workspaceId || null,
      workspace,
      symbols,
      watchlists: [],
      memorySnapshots: [],
      signalBundles: [],
      dueActionItems: [],
      readinessAssessments: [],
      operatorReviews: [],
      signalDigests: [],
      latestDigestItems: [],
      failures,
      backendUnavailable,
      generatedAt,
    });
  }

  const backendBriefResult = await getLatestWorkspaceDailyBrief({ workspaceId: workspace.id });
  if (backendBriefResult.ok) {
    return composeWorkspaceBriefFromBackend({
      appName: env.appName,
      apiBaseUrl: env.apiBaseUrl,
      requestedWorkspaceId: params.workspaceId || null,
      workspace,
      generatedAt: backendBriefResult.data.generated_at,
      brief: backendBriefResult.data,
      failures,
      backendUnavailable,
    });
  }
  if (!backendBriefResult.error.missing && backendBriefResult.error.status !== 0) {
    failures.push(toBriefFailure("Backend daily brief", backendBriefResult));
  }

  const [
    watchlistsResult,
    memoryResult,
    scheduledScansResult,
    dueScansResult,
    analysisRunsResult,
    dueActionItemsResult,
    readinessAssessmentsResult,
    operatorReviewsResult,
    signalDigestsResult,
  ] = await Promise.all([
    listWatchlists(workspace.id),
    listMarketMemorySnapshots(workspace.id),
    listScheduledScanConfigs(workspace.id),
    listDueScheduledScanConfigs(workspace.id),
    listAnalysisRuns(workspace.id),
    listDueActionItems(workspace.id),
    listDecisionReadinessAssessments(workspace.id),
    listOperatorReviewItems(workspace.id),
    listSignalDigests(workspace.id),
  ]);

  const rawWatchlists = readResult("Watchlists", watchlistsResult, [], failures);
  const memorySnapshots = readResult("Market memory", memoryResult, [], failures);
  readResult<ScheduledScanConfig[]>("Scheduled scans", scheduledScansResult, [], failures);
  readResult<ScheduledScanConfig[]>("Due scan configs", dueScansResult, [], failures);
  const analysisRuns = readResult("Analysis runs", analysisRunsResult, [], failures);
  const dueActionItems = readResult("Backend action items", dueActionItemsResult, [], failures);
  const readinessAssessments = readDecisionReadiness(readinessAssessmentsResult, failures);
  const operatorReviews = readResult<OperatorReviewItem[]>("Operator reviews", operatorReviewsResult, [], failures);
  const signalDigests = readResult<SignalDigestRun[]>("Signal digests", signalDigestsResult, [], failures);
  const latestDigestItems = await fetchLatestDigestItems(signalDigests, failures);
  const watchlists = await fetchWatchlistItems(rawWatchlists, failures);
  const signalBundles = await fetchSignalBundles(memorySnapshots, analysisRuns, failures);

  return composeBrief({
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    requestedWorkspaceId: params.workspaceId || null,
    workspace,
    symbols,
    watchlists,
    memorySnapshots,
    signalBundles,
    dueActionItems,
    readinessAssessments,
    operatorReviews,
    signalDigests,
    latestDigestItems,
    failures,
    backendUnavailable,
    generatedAt,
  });
}

async function fetchLatestDigestItems(
  signalDigests: SignalDigestRun[],
  failures: BriefFailure[],
): Promise<SignalDigestItem[]> {
  const latestDigest = signalDigests[0] || null;
  if (!latestDigest) {
    return [];
  }
  return readResult("Signal digest items", await listSignalDigestItems(latestDigest.id), [], failures);
}

async function fetchWatchlistItems(
  watchlists: Watchlist[],
  failures: BriefFailure[],
): Promise<BriefWatchlistWithItems[]> {
  const results = await Promise.all(
    watchlists.map(async (watchlist) => ({
      watchlist,
      result: await listWatchlistItems(watchlist.id),
    })),
  );
  return results.map(({ watchlist, result }) => ({
    watchlist,
    items: readResult<WatchlistItem[]>(`${watchlist.name} items`, result, [], failures),
  }));
}

async function fetchSignalBundles(
  memorySnapshots: Array<{ latest_signal_id: UUID | null; latest_analysis_run_id: UUID | null; updated_at: string }>,
  analysisRuns: Array<{ id: UUID; updated_at: string }>,
  failures: BriefFailure[],
): Promise<BriefSignalBundle[]> {
  const signalIds = unique(
    memorySnapshots
      .slice()
      .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
      .flatMap((snapshot) => (snapshot.latest_signal_id ? [snapshot.latest_signal_id] : [])),
  ).slice(0, 10);
  const fallbackAnalysisRunIds = unique(
    [
      ...memorySnapshots.flatMap((snapshot) => (snapshot.latest_analysis_run_id ? [snapshot.latest_analysis_run_id] : [])),
      ...analysisRuns.map((run) => run.id),
    ],
  ).slice(0, 10);
  const directSignalResults = await Promise.all(signalIds.map((signalId) => getSignal(signalId)));
  const directSignals = directSignalResults.flatMap((result, index) => {
    if (result.ok) {
      return [result.data];
    }
    failures.push(toBriefFailure(`Signals ${signalIds[index]}`, result));
    return [];
  });
  const existingSignalIds = new Set(directSignals.map((signal) => signal.signal.id));
  const fallbackResults = directSignals.length
    ? []
    : await Promise.all(fallbackAnalysisRunIds.map((analysisRunId) => getAnalysisRunSignal(analysisRunId)));
  const fallbackSignals = fallbackResults.flatMap((result, index) => {
    if (result.ok && !existingSignalIds.has(result.data.signal.id)) {
      existingSignalIds.add(result.data.signal.id);
      return [result.data];
    }
    if (!result.ok) {
      failures.push(toBriefFailure(`Signals ${fallbackAnalysisRunIds[index]}`, result));
    }
    return [];
  });
  const selectedSignals = [...directSignals, ...fallbackSignals];
  const bundleResults = await Promise.all(
    selectedSignals.map(async (signal) => {
      const [setupContextResult, outcomesResult, readinessResult] = await Promise.all([
        getSignalSetupContext(signal.signal.id),
        listSignalOutcomes(signal.signal.id),
        getLatestSignalReadiness(signal.signal.id),
      ]);
      const setupContext = readNullableResult(`Setup context ${signal.signal.id}`, setupContextResult, failures);
      const outcomes = readResult(`Signal outcomes ${signal.signal.id}`, outcomesResult, [], failures);
      const readiness = readNullableResult(`Decision readiness ${signal.signal.id}`, readinessResult, failures);
      return {
        signal,
        setupContext,
        outcomes,
        readiness,
      };
    }),
  );
  return bundleResults;
}

function readDecisionReadiness(
  result: ApiResult<DecisionReadinessAssessmentListResponse>,
  failures: BriefFailure[],
) {
  const response = readNullableResult("Decision readiness", result, failures);
  return response?.assessments || [];
}

function readResult<T>(label: string, result: ApiResult<T>, fallback: T, failures: BriefFailure[]): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(toBriefFailure(label, result));
  return fallback;
}

function readNullableResult<T>(label: string, result: ApiResult<T>, failures: BriefFailure[]): T | null {
  if (result.ok) {
    return result.data;
  }
  failures.push(toBriefFailure(label, result));
  return null;
}

function isBackendUnavailable(
  healthResult: ApiResult<HealthResponse>,
  workspacesResult: ApiResult<Workspace[]>,
): boolean {
  return (
    (!healthResult.ok && healthResult.error.status === 0) ||
    (!workspacesResult.ok && workspacesResult.error.status === 0)
  );
}

function unique<T>(values: T[]): T[] {
  return Array.from(new Set(values));
}

function composeWorkspaceBriefFromBackend(input: {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: string | null;
  workspace: Workspace;
  generatedAt: string;
  brief: {
    id: UUID;
    period_start: string;
    period_end: string;
    timezone: string;
    watchlist_id: UUID | null;
    summary_json: JsonRecord;
    sections_json: JsonRecord;
    warnings_json: JsonRecord[];
  };
  failures: BriefFailure[];
  backendUnavailable: boolean;
}): WorkspaceBrief {
  const counts = readRecord(input.brief.summary_json.counts);
  const reviewFirst = readSection(input.brief.sections_json.review_first);
  const needsConfirmation = readSection(input.brief.sections_json.needs_confirmation);
  const avoidConditions = readSection(input.brief.sections_json.avoid_conditions);
  const dataFreshness = readSection(input.brief.sections_json.data_freshness);
  const outcomeUpdates = readSection(input.brief.sections_json.outcome_updates);
  const watchNext = readSection(input.brief.sections_json.watch_next);
  const pendingActions = readSection(input.brief.sections_json.pending_actions);
  const marketContext = readSection(input.brief.sections_json.market_context);
  const backendWarnings = input.brief.warnings_json.map((warning) => ({
    label: "Backend daily brief",
    status: 200,
    message: readString(warning.message) || readString(warning.code) || "Daily brief warning",
    missing: false,
  }));

  return {
    appName: input.appName,
    apiBaseUrl: input.apiBaseUrl,
    workspace: { id: input.workspace.id, name: input.workspace.name },
    requestedWorkspaceId: input.requestedWorkspaceId,
    generatedAt: input.generatedAt,
    periodStart: input.brief.period_start,
    periodEnd: input.brief.period_end,
    timezone: input.brief.timezone,
    watchlistId: input.brief.watchlist_id,
    sourceLabel: "Backend daily brief",
    backendUnavailable: input.backendUnavailable,
    summary: {
      totalSymbolsReviewed: readNumber(counts.total_symbols_reviewed),
      freshSymbols: readNumber(counts.fresh_symbols),
      staleOrDegradedSymbols: readNumber(counts.stale_degraded_symbols),
      activeSetupCount: readNumber(counts.review_first_count),
      reviewRecommendedCount:
        readNumber(counts.needs_confirmation_count) + readNumber(counts.avoid_condition_count),
      recentOutcomeUpdateCount: readNumber(counts.recent_outcome_count),
      pendingBackendActionCount: readNumber(counts.pending_backend_action_count),
    },
    marketFocus: marketContext.slice(0, 8).map(toMarketFocusItem),
    activeSetups: reviewFirst.slice(0, 8).map(toActiveSetupItem),
    avoidConditions: avoidConditions.slice(0, 12).map(toAvoidConditionItem),
    outcomeUpdates: outcomeUpdates.slice(0, 8).map(toOutcomeUpdateItem),
    pendingActions: pendingActions.slice(0, 8).map(toPendingActionItem),
    dataQualityIssues: dataFreshness.slice(0, 10).map(toDataQualityIssue),
    watchNext: watchNext.slice(0, 8).map(toWatchNextItem),
    reviewNeeded: needsConfirmation.slice(0, 8).map(toReviewNeededItem),
    digestSummaries: [...reviewFirst, ...needsConfirmation, ...avoidConditions, ...outcomeUpdates]
      .slice(0, 6)
      .map(toDigestSummary),
    sectionStatuses: {
      workspace: readyStatus("Workspace", true),
      marketFocus: readyStatus("Market focus", marketContext.length > 0),
      activeSetups: readyStatus("Active setups", reviewFirst.length > 0),
      avoidConditions: readyStatus("Avoid conditions", avoidConditions.length > 0),
      outcomeUpdates: readyStatus("Outcome updates", outcomeUpdates.length > 0),
      pendingActions: readyStatus("Pending actions", pendingActions.length > 0),
      dataQuality: readyStatus("Data quality", dataFreshness.length > 0),
      watchNext: readyStatus("Watch next", watchNext.length > 0),
      reviewNeeded: readyStatus("Review needed", needsConfirmation.length > 0),
      digests: readyStatus("Backend daily brief", true),
    },
    failures: [...input.failures, ...backendWarnings],
  };
}

type BackendSectionItem = JsonRecord & {
  id?: string;
  item_type?: string;
  priority?: string;
  title?: string;
  summary?: string;
  reason?: string;
  symbol_id?: string | null;
  signal_id?: string | null;
  outcome_id?: string | null;
  action_item_id?: string | null;
  source_type?: string | null;
  source_id?: string | null;
  metadata?: JsonRecord;
};

function toMarketFocusItem(item: BackendSectionItem) {
  return {
    id: sectionItemId(item, "market"),
    symbolId: readUuid(item.symbol_id) || "",
    symbol: readMetadataSymbol(item) || "Workspace",
    displayName: readMetadataSymbol(item) || "Market context",
    timeframe: readString(item.metadata?.timeframe) || "Context",
    latestBias: readString(item.metadata?.bias) || "neutral",
    confidenceLabel: readString(item.metadata?.confidence_label) || "Context",
    freshnessLabel: "fresh",
    dataQualityLabel: readString(item.metadata?.data_quality_label) || "available",
    marketRegimeLabel: readString(item.metadata?.trend_regime) || readString(item.title) || "Context",
    marketSessionLabel: readString(item.metadata?.session_label) || "Context",
    setupQualityLabel: readString(item.metadata?.agreement_label) || "Context",
    topWarning: readString(item.reason) || "Review context",
    signalId: readUuid(item.signal_id),
  };
}

function toActiveSetupItem(item: BackendSectionItem): BriefActiveSetupItem {
  const signalId = readUuid(item.signal_id) || "";
  return {
    signalId,
    symbolId: readUuid(item.symbol_id) || "",
    symbol: readMetadataSymbol(item) || "Setup",
    timeframe: readString(item.metadata?.timeframe) || "Context",
    bias: readString(item.metadata?.bias) || "directional context",
    patternType: readString(item.metadata?.pattern_type) || "Setup context",
    confidenceLabel: readString(item.metadata?.confidence_label) || "Context",
    setupQualityLabel: readString(item.metadata?.setup_quality_label) || "Context",
    keyEvidence: [readString(item.reason) || readString(item.summary) || "Review recommended"],
    invalidationContext: null,
    waitCondition: null,
    reviewLink: signalId ? `/signals/${signalId}` : "/brief",
  };
}

function toAvoidConditionItem(item: BackendSectionItem): BriefAvoidConditionItem {
  return {
    id: sectionItemId(item, "avoid"),
    symbolId: readUuid(item.symbol_id),
    symbol: readMetadataSymbol(item) || "Workspace",
    timeframe: readString(item.metadata?.timeframe),
    condition: readString(item.title) || "Avoid condition",
    reason: readString(item.reason) || readString(item.summary) || "Review context",
    severity: readString(item.priority) || "normal",
    source: readString(item.source_type) || "Daily brief",
    signalId: readUuid(item.signal_id),
  };
}

function toOutcomeUpdateItem(item: BackendSectionItem): BriefOutcomeUpdateItem {
  return {
    id: sectionItemId(item, "outcome"),
    signalId: readUuid(item.signal_id) || "",
    symbolId: readUuid(item.symbol_id) || "",
    symbol: readMetadataSymbol(item) || "Outcome",
    timeframe: readString(item.metadata?.timeframe) || "Context",
    horizon: `${readNumber(item.metadata?.horizon_minutes)} min`,
    outcomeLabel: readString(item.metadata?.outcome_label) || "outcome update",
    observationLabel: readString(item.summary) || "Outcome update",
    safeSummary: readString(item.reason) || "Observed outcome update available.",
  };
}

function toPendingActionItem(item: BackendSectionItem): BriefPendingActionItem {
  return {
    id: readUuid(item.action_item_id) || sectionItemId(item, "action"),
    actionType: readString(item.metadata?.action_type) || readString(item.source_type) || "backend follow-up",
    status: readString(item.metadata?.status) || "pending",
    dueTime: readString(item.metadata?.due_at),
    source: readString(item.source_type) || "Daily brief",
    safeLabel: readString(item.summary) || "Backend-safe action due",
  };
}

function toDataQualityIssue(item: BackendSectionItem): BriefDataQualityIssue {
  return {
    id: sectionItemId(item, "data"),
    symbolId: readUuid(item.symbol_id),
    symbol: readMetadataSymbol(item) || "Workspace",
    timeframe: readString(item.metadata?.timeframe),
    label: readString(item.title) || "Data freshness",
    detail: readString(item.reason) || readString(item.summary) || "Review data freshness",
    severity: readString(item.priority) || "normal",
    source: readString(item.source_type) || "Daily brief",
  };
}

function toWatchNextItem(item: BackendSectionItem): BriefWatchNextItem {
  return {
    id: sectionItemId(item, "watch"),
    symbolId: readUuid(item.symbol_id) || "",
    symbol: readMetadataSymbol(item) || "Workspace",
    timeframe: readString(item.metadata?.timeframe) || "Context",
    observation: readString(item.summary) || "Watch next",
    reason: readString(item.reason) || "Review context",
    sourceArtifact: readString(item.source_type) || "Daily brief",
    signalId: readUuid(item.signal_id),
  };
}

function toReviewNeededItem(item: BackendSectionItem): BriefReviewNeededItem {
  return {
    id: sectionItemId(item, "review"),
    label: readString(item.title) || "Needs confirmation",
    reason: readString(item.reason) || readString(item.summary) || "Review context",
    priority: readString(item.priority) || "normal",
    source: readString(item.source_type) || "Daily brief",
    signalId: readUuid(item.signal_id),
  };
}

function toDigestSummary(item: BackendSectionItem): BriefDigestSummary {
  return {
    id: sectionItemId(item, "digest"),
    title: readString(item.title) || "Daily brief item",
    summary: readString(item.summary) || "Daily brief context",
    priority: readString(item.priority) || "normal",
    itemType: readString(item.item_type) || "daily_brief",
    signalId: readUuid(item.signal_id),
  };
}

function readyStatus(label: string, hasData: boolean): BriefSectionStatus {
  if (!hasData) {
    return {
      state: "empty",
      label: `${label} empty`,
      message: "No matching backend brief items were returned.",
    };
  }
  return {
    state: "ready",
    label,
    message: "Section data loaded from backend daily brief.",
  };
}

function readSection(value: unknown): BackendSectionItem[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(isRecord).map((item) => item as BackendSectionItem);
}

function readRecord(value: unknown): JsonRecord {
  return isRecord(value) ? (value as JsonRecord) : {};
}

function readString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function readUuid(value: unknown): UUID | null {
  return readString(value);
}

function readNumber(value: unknown): number {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function sectionItemId(item: BackendSectionItem, fallback: string): string {
  return readString(item.id) || readString(item.source_id) || readString(item.signal_id) || fallback;
}

function readMetadataSymbol(item: BackendSectionItem): string | null {
  const title = readString(item.title);
  return readString(item.metadata?.symbol) || (title ? title.split(" ")[0] : null);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
