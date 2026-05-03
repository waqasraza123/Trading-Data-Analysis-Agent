import { getPublicEnv } from "@/config/env";
import { listSignalDigests, listSignalDigestItems } from "@/lib/api/signal-digests";
import { outcomeReviewFailure, type OutcomeReviewData, type OutcomeReviewFailure, type OutcomeReviewFilters, type OutcomeReviewQueueItem, type OutcomeReviewSummary } from "@/lib/review/types";
import { apiGet } from "./client";
import { listJournalEntries } from "./journal";
import { listAnalysisRuns, listSymbols, listWorkspaces } from "./market";
import { listSignalOutcomes } from "./outcomes";
import { getAnalysisRunSignal, getSignal } from "./signals";
import { getSignalSetupContext } from "./setup-context";
import type {
  AnalysisRun,
  ApiFailure,
  ApiResult,
  JournalEntry,
  SignalClassification,
  SignalDigestItem,
  SignalOutcome,
  SetupContext,
  SymbolRead,
  UUID,
} from "./types";
import type {
  CalibrationRecommendation,
  CohortDriftResult,
  ConfidenceCalibrationBin,
  ConfidenceCalibrationRun,
  OutcomePerformanceSummary,
  PatternAttributionResult,
  PatternAttributionRun,
  PatternOutcomeDiagnostic,
  StrategyProfileDiagnostic,
} from "@/lib/review/types";

const signalCandidateLimit = 48;

export async function getOutcomeReviewData(params: Record<string, string | undefined>): Promise<OutcomeReviewData> {
  const env = getPublicEnv();
  const filters = parseOutcomeReviewFilters(params);
  const failures: OutcomeReviewFailure[] = [];
  const [workspacesResult, symbolsResult] = await Promise.all([listWorkspaces(), listSymbols()]);
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const symbols = readResult("Symbols", symbolsResult, [], failures);
  const workspace = workspaces.find((candidate) => candidate.id === filters.workspaceId) || workspaces[0] || null;

  if (!workspace) {
    return emptyOutcomeReviewData(env.appName, env.apiBaseUrl, filters, workspaces, symbols, failures);
  }

  const resolvedFilters = { ...filters, workspaceId: workspace.id };
  const [
    analysisRunsResult,
    journalEntriesResult,
    digestsResult,
    patternPerformanceResult,
    profileDiagnosticsResult,
    patternDiagnosticsResult,
    recommendationsResult,
    calibrationRunsResult,
    cohortDriftResult,
    patternAttributionRunsResult,
  ] = await Promise.all([
    listAnalysisRuns(workspace.id, resolvedFilters.symbolId),
    listJournalEntries({ workspaceId: workspace.id, limit: 500 }),
    listSignalDigests(workspace.id),
    listPatternOutcomePerformance(workspace.id, resolvedFilters.horizonMinutes || 30),
    listProfileDiagnostics(workspace.id, resolvedFilters.horizonMinutes),
    listPatternDiagnostics(workspace.id, resolvedFilters.horizonMinutes),
    listCalibrationRecommendations(workspace.id),
    listConfidenceCalibrationRuns(workspace.id),
    listRecentCohortDrift(workspace.id),
    listPatternAttributionRuns(workspace.id),
  ]);

  const analysisRuns = readResult("Analysis runs", analysisRunsResult, [], failures);
  const journalEntries = readResult("Journal entries", journalEntriesResult, [], failures);
  const digests = readResult("Signal digests", digestsResult, [], failures);
  const patternPerformance = readResult("Outcome pattern summaries", patternPerformanceResult, [], failures);
  const profileDiagnostics = readResult("Profile diagnostics", profileDiagnosticsResult, [], failures);
  const patternDiagnostics = readResult("Pattern diagnostics", patternDiagnosticsResult, [], failures);
  const recommendations = readResult("Calibration recommendations", recommendationsResult, [], failures);
  const calibrationRuns = readResult("Confidence calibration runs", calibrationRunsResult, [], failures);
  const cohortDrift = readResult("Cohort drift", cohortDriftResult, [], failures);
  const patternAttributionRuns = readResult("Pattern attribution runs", patternAttributionRunsResult, [], failures);
  const calibrationRun = calibrationRuns[0] || null;
  const patternAttributionRun = patternAttributionRuns[0] || null;
  const [calibrationBinsResult, patternAttributionResultsResult, digestItems] = await Promise.all([
    calibrationRun ? listConfidenceCalibrationBins(calibrationRun.id) : Promise.resolve(null),
    patternAttributionRun ? listPatternAttributionResults(patternAttributionRun.id) : Promise.resolve(null),
    loadDigestItems(digests.slice(0, 2), failures),
  ]);
  const calibrationBins = calibrationBinsResult
    ? readResult("Confidence calibration bins", calibrationBinsResult, [], failures)
    : [];
  const patternAttributionResults = patternAttributionResultsResult
    ? readResult("Pattern attribution results", patternAttributionResultsResult, [], failures)
    : [];
  const signalRefs = await resolveSignalRefs(analysisRuns, failures);
  const symbolMap = new Map(symbols.map((symbol) => [symbol.id, symbol]));
  const allQueue = await Promise.all(
    signalRefs.slice(0, signalCandidateLimit).map((signal) =>
      enrichOutcomeReviewItem(
        signal,
        analysisRuns.find((run) => run.id === signal.analysis_run_id) || null,
        symbolMap.get(signal.signal.symbol_id) || null,
        journalEntries,
        digestItems,
        failures,
      ),
    ),
  );
  const queue = sortQueue(allQueue.filter((item): item is OutcomeReviewQueueItem => Boolean(item))).filter((item) =>
    matchesOutcomeReviewFilters(item, resolvedFilters),
  );

  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    requestedWorkspaceId: filters.workspaceId || null,
    workspace,
    workspaces,
    symbols,
    filters: resolvedFilters,
    queue,
    allQueue: sortQueue(allQueue.filter((item): item is OutcomeReviewQueueItem => Boolean(item))),
    summary: summarizeQueue(queue),
    patternPerformance,
    profileDiagnostics,
    patternDiagnostics,
    recommendations,
    calibrationRun,
    calibrationBins,
    cohortDrift,
    patternAttributionRun,
    patternAttributionResults,
    digests,
    failures,
    lastLoadedAt: new Date().toISOString(),
  };
}

function parseOutcomeReviewFilters(params: Record<string, string | undefined>): OutcomeReviewFilters {
  return {
    workspaceId: params.workspaceId,
    symbolId: params.symbolId,
    timeframe: params.timeframe,
    horizonMinutes: parsePositiveNumber(params.horizonMinutes),
    outcomeLabel: params.outcomeLabel,
    onlyMissingJournal: params.onlyMissingJournal === "1" || params.onlyMissingJournal === "true",
  };
}

function parsePositiveNumber(value: string | undefined): number | undefined {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

function emptyOutcomeReviewData(
  appName: string,
  apiBaseUrl: string,
  filters: OutcomeReviewFilters,
  workspaces: OutcomeReviewData["workspaces"],
  symbols: SymbolRead[],
  failures: OutcomeReviewFailure[],
): OutcomeReviewData {
  return {
    appName,
    apiBaseUrl,
    requestedWorkspaceId: filters.workspaceId || null,
    workspace: null,
    workspaces,
    symbols,
    filters,
    queue: [],
    allQueue: [],
    summary: summarizeQueue([]),
    patternPerformance: [],
    profileDiagnostics: [],
    patternDiagnostics: [],
    recommendations: [],
    calibrationRun: null,
    calibrationBins: [],
    cohortDrift: [],
    patternAttributionRun: null,
    patternAttributionResults: [],
    digests: [],
    failures,
    lastLoadedAt: new Date().toISOString(),
  };
}

async function resolveSignalRefs(
  analysisRuns: AnalysisRun[],
  failures: OutcomeReviewFailure[],
): Promise<SignalClassification[]> {
  const signalResults = await Promise.all(
    analysisRuns.slice(0, signalCandidateLimit).map(async (run) => {
      const result = await getAnalysisRunSignal(run.id);
      if (result.ok) {
        return result.data;
      }
      if (!result.error.missing) {
        failures.push(outcomeReviewFailure(`Analysis run signal ${run.id}`, result.error));
      }
      return null;
    }),
  );
  const uniqueSignals = new Map<UUID, SignalClassification>();
  for (const signal of signalResults) {
    if (signal) {
      uniqueSignals.set(signal.signal.id, signal);
    }
  }
  return Array.from(uniqueSignals.values());
}

async function enrichOutcomeReviewItem(
  signal: SignalClassification,
  analysisRun: AnalysisRun | null,
  symbol: SymbolRead | null,
  journalEntries: JournalEntry[],
  digestItems: SignalDigestItem[],
  failures: OutcomeReviewFailure[],
): Promise<OutcomeReviewQueueItem | null> {
  const missingContexts: string[] = [];
  const [outcomesResult, setupContextResult] = await Promise.all([
    listSignalOutcomes(signal.signal.id),
    getSignalSetupContext(signal.signal.id),
  ]);
  const outcomes = readOptionalList("Signal outcomes", outcomesResult, missingContexts, failures);
  if (outcomes.length === 0) {
    return null;
  }
  const setupContext = readOptionalValue("Setup context", setupContextResult, missingContexts, failures);
  const latestOutcome = pickLatestOutcome(outcomes);
  return {
    id: latestOutcome.id,
    signal,
    analysisRun,
    symbol,
    outcomes: sortOutcomes(outcomes),
    latestOutcome,
    journalEntry: journalEntries.find((entry) => entry.signal_id === signal.signal.id) || null,
    setupContext,
    digestItems: digestItems.filter((item) => item.signal_id === signal.signal.id || item.outcome_id === latestOutcome.id),
    missingContexts,
  };
}

function pickLatestOutcome(outcomes: SignalOutcome[]): SignalOutcome {
  return sortOutcomes(outcomes)[0];
}

function sortOutcomes(outcomes: SignalOutcome[]): SignalOutcome[] {
  return [...outcomes].sort((left, right) => {
    const rightTime = Date.parse(right.updated_at || right.created_at || right.future_window_end);
    const leftTime = Date.parse(left.updated_at || left.created_at || left.future_window_end);
    if (rightTime !== leftTime) {
      return rightTime - leftTime;
    }
    return right.horizon_minutes - left.horizon_minutes;
  });
}

function matchesOutcomeReviewFilters(item: OutcomeReviewQueueItem, filters: OutcomeReviewFilters): boolean {
  return (
    matches(item.signal.signal.symbol_id, filters.symbolId) &&
    matches(item.signal.signal.timeframe, filters.timeframe) &&
    matches(String(item.latestOutcome.horizon_minutes), filters.horizonMinutes ? String(filters.horizonMinutes) : undefined) &&
    matches(item.latestOutcome.outcome_label, filters.outcomeLabel) &&
    (!filters.onlyMissingJournal || !item.journalEntry)
  );
}

function matches(value: string | null | undefined, filter: string | undefined): boolean {
  return !filter || value === filter;
}

function sortQueue(items: OutcomeReviewQueueItem[]): OutcomeReviewQueueItem[] {
  return [...items].sort((left, right) => Date.parse(right.latestOutcome.updated_at) - Date.parse(left.latestOutcome.updated_at));
}

function summarizeQueue(queue: OutcomeReviewQueueItem[]): OutcomeReviewSummary {
  return {
    queueCount: queue.length,
    reviewedCount: queue.filter((item) => item.journalEntry).length,
    missingJournalCount: queue.filter((item) => !item.journalEntry).length,
    continuationCount: queue.filter((item) => ["continuation", "partial_follow_through"].includes(item.latestOutcome.outcome_label)).length,
    reversalCount: queue.filter((item) => item.latestOutcome.outcome_label === "reversal").length,
    noFollowThroughCount: queue.filter((item) => ["no_follow_through", "sideways_after_signal"].includes(item.latestOutcome.outcome_label)).length,
    insufficientDataCount: queue.filter((item) => item.latestOutcome.outcome_label === "insufficient_data").length,
  };
}

async function loadDigestItems(
  digests: OutcomeReviewData["digests"],
  failures: OutcomeReviewFailure[],
): Promise<SignalDigestItem[]> {
  const results = await Promise.all(digests.map((digest) => listSignalDigestItems(digest.id)));
  return results.flatMap((result, index) => {
    if (result.ok) {
      return result.data;
    }
    if (!result.error.missing) {
      failures.push(outcomeReviewFailure(`Signal digest items ${digests[index].id}`, result.error));
    }
    return [];
  });
}

function listPatternOutcomePerformance(
  workspaceId: UUID,
  horizonMinutes: number,
): Promise<ApiResult<OutcomePerformanceSummary[]>> {
  return apiGet<OutcomePerformanceSummary[]>("/outcomes/performance/patterns", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      horizon_minutes: horizonMinutes,
    },
  });
}

function listProfileDiagnostics(
  workspaceId: UUID,
  horizonMinutes?: number,
): Promise<ApiResult<StrategyProfileDiagnostic[]>> {
  return apiGet<StrategyProfileDiagnostic[]>("/profile-diagnostics/strategy-profiles", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      horizon_minutes: horizonMinutes,
      limit: 8,
    },
  });
}

function listPatternDiagnostics(
  workspaceId: UUID,
  horizonMinutes?: number,
): Promise<ApiResult<PatternOutcomeDiagnostic[]>> {
  return apiGet<PatternOutcomeDiagnostic[]>("/profile-diagnostics/patterns", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      horizon_minutes: horizonMinutes,
      limit: 8,
    },
  });
}

function listCalibrationRecommendations(workspaceId: UUID): Promise<ApiResult<CalibrationRecommendation[]>> {
  return apiGet<CalibrationRecommendation[]>("/profile-diagnostics/recommendations", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 8,
    },
  });
}

function listConfidenceCalibrationRuns(workspaceId: UUID): Promise<ApiResult<ConfidenceCalibrationRun[]>> {
  return apiGet<ConfidenceCalibrationRun[]>("/confidence-calibration/runs", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 1,
    },
  });
}

function listConfidenceCalibrationBins(runId: UUID): Promise<ApiResult<ConfidenceCalibrationBin[]>> {
  return apiGet<ConfidenceCalibrationBin[]>(`/confidence-calibration/runs/${runId}/bins`, {
    optional: true,
    query: {
      limit: 12,
    },
  });
}

function listRecentCohortDrift(workspaceId: UUID): Promise<ApiResult<CohortDriftResult[]>> {
  return apiGet<CohortDriftResult[]>("/cohort-drift/results/recent", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 8,
    },
  });
}

function listPatternAttributionRuns(workspaceId: UUID): Promise<ApiResult<PatternAttributionRun[]>> {
  return apiGet<PatternAttributionRun[]>("/pattern-attribution/runs", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 1,
    },
  });
}

function listPatternAttributionResults(runId: UUID): Promise<ApiResult<PatternAttributionResult[]>> {
  return apiGet<PatternAttributionResult[]>(`/pattern-attribution/runs/${runId}/results`, {
    optional: true,
    query: {
      limit: 8,
    },
  });
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: OutcomeReviewFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(outcomeReviewFailure(label, result.error));
  return fallback;
}

function readOptionalList<T>(
  label: string,
  result: ApiResult<T[]>,
  missingContexts: string[],
  failures: OutcomeReviewFailure[],
): T[] {
  if (result.ok) {
    return result.data;
  }
  missingContexts.push(label);
  if (!result.error.missing) {
    failures.push(outcomeReviewFailure(label, result.error));
  }
  return [];
}

function readOptionalValue<T>(
  label: string,
  result: ApiResult<T>,
  missingContexts: string[],
  failures: OutcomeReviewFailure[],
): T | null {
  if (result.ok) {
    return result.data;
  }
  missingContexts.push(label);
  if (!result.error.missing) {
    failures.push(outcomeReviewFailure(label, result.error));
  }
  return null;
}

export async function getSignalForOutcomeReview(signalId: UUID): Promise<ApiResult<SignalClassification>> {
  return getSignal(signalId);
}

export function outcomeReviewApiFailure(result: ApiFailure): OutcomeReviewFailure {
  return outcomeReviewFailure("API request", result.error);
}
