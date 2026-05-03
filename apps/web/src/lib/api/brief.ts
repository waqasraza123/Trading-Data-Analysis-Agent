import { getPublicEnv } from "@/config/env";
import {
  composeBrief,
  toBriefFailure,
  type BriefSignalBundle,
  type BriefWatchlistWithItems,
} from "@/lib/brief/composeBrief";
import type { BriefFailure, WorkspaceBrief } from "@/lib/brief/types";
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
