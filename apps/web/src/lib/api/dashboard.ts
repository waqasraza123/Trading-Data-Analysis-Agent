import { getPublicEnv } from "@/config/env";
import { listAnalysisRuns, listMarketMemorySnapshots, listSymbols, listWorkspaces } from "./market";
import { listSignalOutcomes } from "./outcomes";
import { getLatestSignalReadiness } from "./readiness";
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
  ActionItem,
  AnalysisRun,
  ApiFailure,
  ApiResult,
  DecisionReadinessAssessmentResponse,
  HealthResponse,
  MarketMemorySnapshot,
  ScheduledScanConfig,
  SignalClassification,
  SignalDigestItem,
  SignalDigestRun,
  SignalOutcome,
  SetupContext,
  SymbolRead,
  UUID,
  Watchlist,
  WatchlistItem,
  WorkerStatusResponse,
  Workspace,
} from "./types";

export type DashboardFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type WatchlistWithItems = {
  watchlist: Watchlist;
  items: WatchlistItem[];
};

export type DashboardData = {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: UUID | null;
  workspace: Workspace | null;
  workspaces: Workspace[];
  symbols: SymbolRead[];
  watchlists: WatchlistWithItems[];
  memorySnapshots: MarketMemorySnapshot[];
  scheduledScans: ScheduledScanConfig[];
  dueScans: ScheduledScanConfig[];
  analysisRuns: AnalysisRun[];
  dueActionItems: ActionItem[];
  signalDigests: SignalDigestRun[];
  latestDigestItems: SignalDigestItem[];
  selectedSignal: SignalClassification | null;
  selectedSetupContext: SetupContext | null;
  selectedOutcomes: SignalOutcome[];
  selectedReadiness: DecisionReadinessAssessmentResponse | null;
  health: HealthResponse | null;
  workerStatus: WorkerStatusResponse | null;
  failures: DashboardFailure[];
  lastUpdatedAt: string;
};

export async function getDashboardData(params: {
  workspaceId?: string;
  signalId?: string;
}): Promise<DashboardData> {
  const env = getPublicEnv();
  const failures: DashboardFailure[] = [];
  const [workspacesResult, symbolsResult, healthResult, workerStatusResult] = await Promise.all([
    listWorkspaces(),
    listSymbols(),
    getApiHealth(),
    getWorkerStatus(),
  ]);
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const symbols = readResult("Symbols", symbolsResult, [], failures);
  const health = readNullableResult("API health", healthResult, failures);
  const workerStatus = readNullableResult("Worker status", workerStatusResult, failures);
  const workspace =
    workspaces.find((candidate) => candidate.id === params.workspaceId) || workspaces[0] || null;

  if (!workspace) {
    return {
      appName: env.appName,
      apiBaseUrl: env.apiBaseUrl,
      requestedWorkspaceId: params.workspaceId || null,
      workspace,
      workspaces,
      symbols,
      watchlists: [],
      memorySnapshots: [],
      scheduledScans: [],
      dueScans: [],
      analysisRuns: [],
      dueActionItems: [],
      signalDigests: [],
      latestDigestItems: [],
      selectedSignal: null,
      selectedSetupContext: null,
      selectedOutcomes: [],
      selectedReadiness: null,
      health,
      workerStatus,
      failures,
      lastUpdatedAt: new Date().toISOString(),
    };
  }

  const [
    watchlistsResult,
    memoryResult,
    scheduledScansResult,
    dueScansResult,
    analysisRunsResult,
    dueActionItemsResult,
    signalDigestsResult,
  ] = await Promise.all([
    listWatchlists(workspace.id),
    listMarketMemorySnapshots(workspace.id),
    listScheduledScanConfigs(workspace.id),
    listDueScheduledScanConfigs(workspace.id),
    listAnalysisRuns(workspace.id),
    listDueActionItems(workspace.id),
    listSignalDigests(workspace.id),
  ]);

  const rawWatchlists = readResult("Watchlists", watchlistsResult, [], failures);
  const memorySnapshots = readResult("Market memory", memoryResult, [], failures);
  const scheduledScans = readResult("Scheduled scans", scheduledScansResult, [], failures);
  const dueScans = readResult("Due scan configs", dueScansResult, [], failures);
  const analysisRuns = readResult("Analysis runs", analysisRunsResult, [], failures);
  const dueActionItems = readResult("Backend action items", dueActionItemsResult, [], failures);
  const signalDigests = readResult("Signal digests", signalDigestsResult, [], failures);
  const latestDigest = signalDigests[0] || null;
  const latestDigestItemsResult = latestDigest ? await listSignalDigestItems(latestDigest.id) : null;
  const latestDigestItems = latestDigestItemsResult
    ? readResult("Signal digest items", latestDigestItemsResult, [], failures)
    : [];
  const watchlistItemsResults = await Promise.all(
    rawWatchlists.map(async (watchlist) => ({
      watchlist,
      result: await listWatchlistItems(watchlist.id),
    })),
  );
  const watchlists = watchlistItemsResults.map(({ watchlist, result }) => ({
    watchlist,
    items: readResult(`${watchlist.name} items`, result, [], failures),
  }));

  const latestMemorySignalId =
    memorySnapshots.find((snapshot) => snapshot.latest_signal_id)?.latest_signal_id || null;
  const latestAnalysisRunId = analysisRuns[0]?.id || null;
  const selectedSignal = await resolveSelectedSignal(
    params.signalId || latestMemorySignalId,
    latestAnalysisRunId,
    failures,
  );
  const [selectedOutcomesResult, selectedReadinessResult, selectedSetupContextResult] = selectedSignal
    ? await Promise.all([
        listSignalOutcomes(selectedSignal.signal.id),
        getLatestSignalReadiness(selectedSignal.signal.id),
        getSignalSetupContext(selectedSignal.signal.id),
      ])
    : [null, null, null];
  const selectedOutcomes = selectedOutcomesResult
    ? readResult("Selected signal outcomes", selectedOutcomesResult, [], failures)
    : [];
  const selectedReadiness = selectedReadinessResult
    ? readNullableResult("Selected signal readiness", selectedReadinessResult, failures)
    : null;
  const selectedSetupContext = selectedSetupContextResult
    ? readNullableResult("Selected setup context", selectedSetupContextResult, failures)
    : null;

  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    requestedWorkspaceId: params.workspaceId || null,
    workspace,
    workspaces,
    symbols,
    watchlists,
    memorySnapshots,
    scheduledScans,
    dueScans,
    analysisRuns,
    dueActionItems,
    signalDigests,
    latestDigestItems,
    selectedSignal,
    selectedSetupContext,
    selectedOutcomes,
    selectedReadiness,
    health,
    workerStatus,
    failures,
    lastUpdatedAt: new Date().toISOString(),
  };
}

async function resolveSelectedSignal(
  signalId: UUID | null,
  analysisRunId: UUID | null,
  failures: DashboardFailure[],
): Promise<SignalClassification | null> {
  if (signalId) {
    const result = await getSignal(signalId);
    if (result.ok) {
      return result.data;
    }
    failures.push(toFailure("Selected signal", result));
  }
  if (analysisRunId) {
    const analysisSignalResult = await getAnalysisRunSignal(analysisRunId);
    return readNullableResult("Selected analysis signal", analysisSignalResult, failures);
  }
  return null;
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: DashboardFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return fallback;
}

function readNullableResult<T>(
  label: string,
  result: ApiResult<T>,
  failures: DashboardFailure[],
): T | null {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return null;
}

function toFailure(label: string, result: ApiFailure): DashboardFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}
