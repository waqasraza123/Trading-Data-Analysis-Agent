import { getPublicEnv } from "@/config/env";
import { classifyTriage } from "@/lib/triage/classifyTriage";
import type {
  IntelligenceQualityResponse,
  OperatorReviewItem,
  ScenarioReasoningResponse,
  TriageActionItem,
  TriageBoardData,
  TriageCandidate,
  TriageFailure,
  TriageFilterState,
} from "@/lib/triage/types";
import { apiGet } from "./client";
import { listMarketMemorySnapshots, listSymbols, listWorkspaces } from "./market";
import { listSignalOutcomes } from "./outcomes";
import { getLatestSignalReadiness } from "./readiness";
import { getSignalReport } from "./reports";
import { getAnalysisRunSignal, getSignal } from "./signals";
import { getSignalSetupContext } from "./setup-context";
import type {
  AnalysisRun,
  ApiFailure,
  ApiResult,
  MarketMemorySnapshot,
  SignalClassification,
  UUID,
} from "./types";

const signalCandidateLimit = 48;

export async function getSignalTriageBoard(params: Record<string, string | undefined>): Promise<TriageBoardData> {
  const env = getPublicEnv();
  const filters = parseTriageFilters(params);
  const failures: TriageFailure[] = [];
  const [workspacesResult, symbolsResult] = await Promise.all([listWorkspaces(), listSymbols()]);
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const symbols = readResult("Symbols", symbolsResult, [], failures);
  const workspace = workspaces.find((candidate) => candidate.id === filters.workspaceId) || workspaces[0] || null;

  if (!workspace) {
    return {
      appName: env.appName,
      apiBaseUrl: env.apiBaseUrl,
      requestedWorkspaceId: filters.workspaceId || null,
      workspace: null,
      workspaces,
      symbols,
      filters,
      candidates: [],
      allCandidates: [],
      failures,
      lastLoadedAt: new Date().toISOString(),
    };
  }

  const resolvedFilters = { ...filters, workspaceId: workspace.id };
  const [memoryResult, analysisRunsResult, actionItemsResult, reviewsResult] = await Promise.all([
    listMarketMemorySnapshots(workspace.id),
    listAnalysisRunsForTriage(workspace.id),
    listDueActionItemsForTriage(workspace.id),
    listOperatorReviewsForTriage(workspace.id),
  ]);
  const memorySnapshots = readResult("Market memory", memoryResult, [], failures);
  const analysisRuns = readResult("Analysis runs", analysisRunsResult, [], failures);
  const actionItems = readResult("Backend action items", actionItemsResult, [], failures);
  const reviews = readResult("Operator reviews", reviewsResult, [], failures);
  const signalRefs = await resolveSignalRefs(memorySnapshots, analysisRuns, failures);
  const symbolMap = new Map(symbols.map((symbol) => [symbol.id, symbol]));
  const memoryBySignalId = new Map<UUID, MarketMemorySnapshot>();
  for (const snapshot of memorySnapshots) {
    if (snapshot.latest_signal_id) {
      memoryBySignalId.set(snapshot.latest_signal_id, snapshot);
    }
  }
  const allCandidates = await Promise.all(
    signalRefs.slice(0, signalCandidateLimit).map(async (signal) => {
      const memory = memoryBySignalId.get(signal.signal.id) || null;
      const candidateActionItems = actionItems.filter(
        (item) => item.signal_id === signal.signal.id || item.analysis_run_id === signal.analysis_run_id,
      );
      const candidateReviews = reviews.filter(
        (item) => item.related_signal_id === signal.signal.id || item.related_analysis_run_id === signal.analysis_run_id,
      );
      return enrichCandidate(
        signal,
        symbolMap.get(signal.signal.symbol_id) || null,
        memory,
        candidateActionItems,
        candidateReviews,
        failures,
      );
    }),
  );

  const candidates = allCandidates.filter((candidate) => matchesFilters(candidate, resolvedFilters));

  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    requestedWorkspaceId: filters.workspaceId || null,
    workspace,
    workspaces,
    symbols,
    filters: resolvedFilters,
    candidates: sortCandidates(candidates),
    allCandidates: sortCandidates(allCandidates),
    failures,
    lastLoadedAt: new Date().toISOString(),
  };
}

function parseTriageFilters(params: Record<string, string | undefined>): TriageFilterState {
  return {
    workspaceId: params.workspaceId,
    symbolId: params.symbolId,
    timeframe: params.timeframe,
    bias: params.bias,
    confidence: params.confidence,
    column: parseColumn(params.column),
    freshness: params.freshness,
    profileKey: params.profileKey,
    onlyFresh: parseBoolean(params.onlyFresh),
    onlyReviewRequired: parseBoolean(params.onlyReviewRequired),
  };
}

function parseColumn(value: string | undefined): TriageFilterState["column"] {
  const columns: Array<NonNullable<TriageFilterState["column"]>> = [
    "high_quality_context",
    "needs_confirmation",
    "conflicted",
    "avoid_no_directional_signal",
    "stale_data_issue",
    "review_required",
  ];
  return columns.find((column) => column === value);
}

function parseBoolean(value: string | undefined): boolean {
  return value === "1" || value === "true" || value === "on";
}

async function resolveSignalRefs(
  memorySnapshots: MarketMemorySnapshot[],
  analysisRuns: AnalysisRun[],
  failures: TriageFailure[],
): Promise<SignalClassification[]> {
  const signalIds = uniqueValues(memorySnapshots.map((snapshot) => snapshot.latest_signal_id).filter(isPresent));
  const signalResults = await Promise.all(signalIds.map((signalId) => getSignal(signalId)));
  const signals = signalResults.flatMap((result, index) => {
    if (result.ok) {
      return [result.data];
    }
    failures.push(toFailure(`Signal ${signalIds[index]}`, result));
    return [];
  });
  const knownSignalIds = new Set(signals.map((signal) => signal.signal.id));
  const analysisSignals = await Promise.all(
    analysisRuns.slice(0, signalCandidateLimit).map(async (run) => {
      const result = await getAnalysisRunSignal(run.id);
      if (result.ok) {
        return knownSignalIds.has(result.data.signal.id) ? null : result.data;
      }
      if (!result.error.missing) {
        failures.push(toFailure(`Analysis run signal ${run.id}`, result));
      }
      return null;
    }),
  );
  return [...signals, ...analysisSignals.filter(isPresent)];
}

async function enrichCandidate(
  signal: SignalClassification,
  symbol: TriageCandidate["symbol"],
  memory: MarketMemorySnapshot | null,
  actionItems: TriageActionItem[],
  reviews: OperatorReviewItem[],
  failures: TriageFailure[],
): Promise<TriageCandidate> {
  const missingContexts: string[] = [];
  const [setupContextResult, outcomesResult, readinessResult, reportResult, qualityResult, reasoningResult] = await Promise.all([
    getSignalSetupContext(signal.signal.id),
    listSignalOutcomes(signal.signal.id),
    getLatestSignalReadiness(signal.signal.id),
    getSignalReport(signal.signal.id),
    getSignalQuality(signal.signal.id),
    getLatestSignalReasoning(signal.signal.id),
  ]);
  const setupContext = readOptionalResult("Setup context", setupContextResult, missingContexts, failures);
  const outcomes = readOptionalList("Outcomes", outcomesResult, missingContexts, failures);
  const readiness = readOptionalResult("Readiness", readinessResult, missingContexts, failures);
  const report = readOptionalResult("Intelligence report", reportResult, missingContexts, failures);
  const quality = readOptionalResult("Quality gates", qualityResult, missingContexts, failures);
  const reasoning = readOptionalResult("Reasoning", reasoningResult, missingContexts, failures);
  const input = {
    signal,
    memory,
    setupContext,
    outcomes,
    readiness,
    report,
    quality,
    reasoning,
    reviews,
    actionItems,
    missingContexts,
  };
  return {
    id: signal.signal.id,
    symbol,
    classification: classifyTriage(input),
    ...input,
  };
}

function listAnalysisRunsForTriage(workspaceId: UUID): Promise<ApiResult<AnalysisRun[]>> {
  return apiGet<AnalysisRun[]>("/analysis-runs", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 100,
      offset: 0,
    },
  });
}

function getSignalQuality(signalId: UUID): Promise<ApiResult<IntelligenceQualityResponse>> {
  return apiGet<IntelligenceQualityResponse>(`/intelligence-quality/signals/${signalId}/latest`, { optional: true });
}

function getLatestSignalReasoning(signalId: UUID): Promise<ApiResult<ScenarioReasoningResponse>> {
  return apiGet<ScenarioReasoningResponse>(`/signals/${signalId}/reasoning/scenarios/latest`, { optional: true });
}

function listOperatorReviewsForTriage(workspaceId: UUID): Promise<ApiResult<OperatorReviewItem[]>> {
  return apiGet<OperatorReviewItem[]>("/operator-reviews", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 500,
      offset: 0,
    },
  });
}

function listDueActionItemsForTriage(workspaceId: UUID): Promise<ApiResult<TriageActionItem[]>> {
  return apiGet<TriageActionItem[]>("/action-items/due", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 500,
    },
  });
}

function matchesFilters(candidate: TriageCandidate, filters: TriageFilterState): boolean {
  return (
    matches(candidate.signal.signal.symbol_id, filters.symbolId) &&
    matches(candidate.signal.signal.timeframe, filters.timeframe) &&
    matches(candidate.signal.signal.bias, filters.bias) &&
    matches(candidate.signal.signal.confidence_label, filters.confidence) &&
    matches(candidate.classification.column, filters.column) &&
    matches(candidate.memory?.freshness_label, filters.freshness) &&
    matches(candidate.signal.signal.strategy_profile_key, filters.profileKey) &&
    (!filters.onlyFresh || candidate.memory?.freshness_label === "fresh") &&
    (!filters.onlyReviewRequired || candidate.classification.column === "review_required")
  );
}

function sortCandidates(candidates: TriageCandidate[]): TriageCandidate[] {
  const columnOrder = [
    "review_required",
    "stale_data_issue",
    "conflicted",
    "needs_confirmation",
    "high_quality_context",
    "avoid_no_directional_signal",
  ];
  return [...candidates].sort((left, right) => {
    const columnDelta = columnOrder.indexOf(left.classification.column) - columnOrder.indexOf(right.classification.column);
    if (columnDelta !== 0) {
      return columnDelta;
    }
    return latestTime(right).localeCompare(latestTime(left));
  });
}

function latestTime(candidate: TriageCandidate): string {
  return candidate.memory?.latest_final_candle_time || candidate.signal.signal.created_at || "";
}

function matches(value: string | null | undefined, filter: string | undefined): boolean {
  return !filter || value === filter;
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: TriageFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return fallback;
}

function readOptionalResult<T>(
  label: string,
  result: ApiResult<T>,
  missingContexts: string[],
  failures: TriageFailure[],
): T | null {
  if (result.ok) {
    return result.data;
  }
  missingContexts.push(label);
  if (!result.error.missing) {
    failures.push(toFailure(label, result));
  }
  return null;
}

function readOptionalList<T>(
  label: string,
  result: ApiResult<T[]>,
  missingContexts: string[],
  failures: TriageFailure[],
): T[] {
  if (result.ok) {
    return result.data;
  }
  missingContexts.push(label);
  if (!result.error.missing) {
    failures.push(toFailure(label, result));
  }
  return [];
}

function toFailure(label: string, result: ApiFailure): TriageFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}

function uniqueValues<T>(values: T[]): T[] {
  return Array.from(new Set(values));
}

function isPresent<T>(value: T | null | undefined): value is T {
  return value !== null && value !== undefined;
}
