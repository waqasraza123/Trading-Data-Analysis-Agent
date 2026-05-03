import { getPublicEnv } from "@/config/env";
import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import { listWorkspaces } from "./market";
import { getSignal } from "./signals";
import { getApiHealth, getWorkerStatus } from "./status";
import type {
  ApiFailure,
  ApiResult,
  ScheduledScanConfig,
  SignalClassification,
  SymbolRead,
  UUID,
  Watchlist,
  WatchlistItem,
} from "./types";
import type {
  RunDueScansResponse,
  RunDueScansInput,
  ScannerData,
  ScannerDataSource,
  ScheduledScanRun,
  ScheduledScanRunItem,
  ScheduledScanConfigCreateInput,
  ScheduledScanConfigUpdateInput,
  WatchlistCreateInput,
  WatchlistItemCreateInput,
  WatchlistItemUpdateInput,
  WatchlistUpdateInput,
  WatchlistWithItems,
} from "@/lib/scanner/types";
import { scannerFailure } from "@/lib/scanner/types";

export function listScannerSymbols(): Promise<ApiResult<SymbolRead[]>> {
  return apiGet<SymbolRead[]>("/symbols", {
    query: {
      is_active: true,
      limit: 500,
    },
    optional: true,
  });
}

export function listScannerDataSources(workspaceId: UUID): Promise<ApiResult<ScannerDataSource[]>> {
  return apiGet<ScannerDataSource[]>("/data-sources", {
    query: {
      workspace_id: workspaceId,
      status: "active",
      limit: 500,
    },
    optional: true,
  });
}

export function listScannerWatchlists(workspaceId: UUID): Promise<ApiResult<Watchlist[]>> {
  return apiGet<Watchlist[]>("/market-watchlists", {
    query: {
      workspace_id: workspaceId,
      limit: 100,
    },
    optional: true,
  });
}

export function createScannerWatchlist(input: WatchlistCreateInput): Promise<ApiResult<Watchlist>> {
  return apiPost<Watchlist>("/market-watchlists", input, { optional: true });
}

export function updateScannerWatchlist(
  watchlistId: UUID,
  input: WatchlistUpdateInput,
): Promise<ApiResult<Watchlist>> {
  return apiPatch<Watchlist>(`/market-watchlists/${watchlistId}`, input, { optional: true });
}

export function listScannerWatchlistItems(
  watchlistId: UUID,
  isActive?: boolean,
): Promise<ApiResult<WatchlistItem[]>> {
  return apiGet<WatchlistItem[]>(`/market-watchlists/${watchlistId}/items`, {
    query: {
      is_active: isActive,
      limit: 500,
    },
    optional: true,
  });
}

export function createScannerWatchlistItem(
  watchlistId: UUID,
  input: WatchlistItemCreateInput,
): Promise<ApiResult<WatchlistItem>> {
  return apiPost<WatchlistItem>(`/market-watchlists/${watchlistId}/items`, input, {
    optional: true,
  });
}

export function updateScannerWatchlistItem(
  itemId: UUID,
  input: WatchlistItemUpdateInput,
): Promise<ApiResult<WatchlistItem>> {
  return apiPatch<WatchlistItem>(`/market-watchlist-items/${itemId}`, input, {
    optional: true,
  });
}

export function deactivateScannerWatchlistItem(itemId: UUID): Promise<ApiResult<WatchlistItem>> {
  return apiDelete<WatchlistItem>(`/market-watchlist-items/${itemId}`, { optional: true });
}

export function listScannerScanConfigs(
  workspaceId: UUID,
): Promise<ApiResult<ScheduledScanConfig[]>> {
  return apiGet<ScheduledScanConfig[]>("/scheduled-scan-configs", {
    query: {
      workspace_id: workspaceId,
      limit: 100,
    },
    optional: true,
  });
}

export function createScannerScanConfig(
  input: ScheduledScanConfigCreateInput,
): Promise<ApiResult<ScheduledScanConfig>> {
  return apiPost<ScheduledScanConfig>("/scheduled-scan-configs", input, { optional: true });
}

export function updateScannerScanConfig(
  scanConfigId: UUID,
  input: ScheduledScanConfigUpdateInput,
): Promise<ApiResult<ScheduledScanConfig>> {
  return apiPatch<ScheduledScanConfig>(`/scheduled-scan-configs/${scanConfigId}`, input, {
    optional: true,
  });
}

export function pauseScannerScanConfig(
  scanConfigId: UUID,
): Promise<ApiResult<ScheduledScanConfig>> {
  return apiPost<ScheduledScanConfig>(`/scheduled-scan-configs/${scanConfigId}/pause`, undefined, {
    optional: true,
  });
}

export function resumeScannerScanConfig(
  scanConfigId: UUID,
): Promise<ApiResult<ScheduledScanConfig>> {
  return apiPost<ScheduledScanConfig>(`/scheduled-scan-configs/${scanConfigId}/resume`, undefined, {
    optional: true,
  });
}

export function archiveScannerScanConfig(
  scanConfigId: UUID,
): Promise<ApiResult<ScheduledScanConfig>> {
  return apiPost<ScheduledScanConfig>(`/scheduled-scan-configs/${scanConfigId}/archive`, undefined, {
    optional: true,
  });
}

export function runScannerScanConfig(scanConfigId: UUID): Promise<ApiResult<ScheduledScanRun>> {
  return apiPost<ScheduledScanRun>(`/scheduled-scan-configs/${scanConfigId}/run`, undefined, {
    optional: true,
    timeoutMs: 30000,
  });
}

export function listScannerDueScanConfigs(
  workspaceId: UUID,
): Promise<ApiResult<ScheduledScanConfig[]>> {
  return apiGet<ScheduledScanConfig[]>("/scheduled-scan-configs/due", {
    query: {
      workspace_id: workspaceId,
      limit: 50,
    },
    optional: true,
  });
}

export function runScannerDueScans(input: RunDueScansInput): Promise<ApiResult<RunDueScansResponse>> {
  return apiPost<RunDueScansResponse>("/scheduled-scan-configs/run-due", input, {
    optional: true,
    timeoutMs: 60000,
  });
}

export function getScannerScanRun(scanRunId: UUID): Promise<ApiResult<ScheduledScanRun>> {
  return apiGet<ScheduledScanRun>(`/scheduled-scan-runs/${scanRunId}`, { optional: true });
}

export function listScannerScanRunItems(
  scanRunId: UUID,
): Promise<ApiResult<ScheduledScanRunItem[]>> {
  return apiGet<ScheduledScanRunItem[]>(`/scheduled-scan-runs/${scanRunId}/items`, {
    query: {
      limit: 500,
    },
    optional: true,
  });
}

export async function getScannerData(params: {
  workspaceId?: string;
  runId?: string;
}): Promise<ScannerData> {
  const env = getPublicEnv();
  const failures: ScannerData["failures"] = [];
  const [workspacesResult, symbolsResult, healthResult, workerStatusResult] = await Promise.all([
    listWorkspaces(),
    listScannerSymbols(),
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
      selectedRunId: params.runId || null,
      workspace,
      workspaces,
      symbols,
      dataSources: [],
      watchlists: [],
      scanConfigs: [],
      dueScanConfigs: [],
      recentRuns: [],
      selectedRun: null,
      selectedRunItems: [],
      selectedRunSignals: [],
      health,
      workerStatus,
      failures,
      lastUpdatedAt: new Date().toISOString(),
    };
  }

  const [sourcesResult, watchlistsResult, scanConfigsResult, dueConfigsResult, selectedRunResult] =
    await Promise.all([
      listScannerDataSources(workspace.id),
      listScannerWatchlists(workspace.id),
      listScannerScanConfigs(workspace.id),
      listScannerDueScanConfigs(workspace.id),
      params.runId ? getScannerScanRun(params.runId) : Promise.resolve(null),
    ]);
  const dataSources = readResult("Data sources", sourcesResult, [], failures);
  const rawWatchlists = readResult("Watchlists", watchlistsResult, [], failures);
  const scanConfigs = readResult("Scheduled scan configs", scanConfigsResult, [], failures);
  const dueScanConfigs = readResult("Due scan configs", dueConfigsResult, [], failures);
  const selectedRun = selectedRunResult
    ? readNullableResult("Selected scan run", selectedRunResult, failures)
    : null;
  const watchlists = await loadWatchlistsWithItems(rawWatchlists, failures);
  const selectedRunItemsResult = selectedRun ? await listScannerScanRunItems(selectedRun.id) : null;
  const selectedRunItems = selectedRunItemsResult
    ? readResult("Selected scan run items", selectedRunItemsResult, [], failures)
    : [];
  const selectedRunSignals = await loadSignals(selectedRun?.signal_ids_json || [], failures);
  const recentRuns = selectedRun ? [selectedRun] : [];

  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    requestedWorkspaceId: params.workspaceId || null,
    selectedRunId: params.runId || null,
    workspace,
    workspaces,
    symbols,
    dataSources,
    watchlists,
    scanConfigs,
    dueScanConfigs,
    recentRuns,
    selectedRun,
    selectedRunItems,
    selectedRunSignals,
    health,
    workerStatus,
    failures,
    lastUpdatedAt: new Date().toISOString(),
  };
}

async function loadWatchlistsWithItems(
  watchlists: Watchlist[],
  failures: ScannerData["failures"],
): Promise<WatchlistWithItems[]> {
  const results = await Promise.all(
    watchlists.map(async (watchlist) => ({
      watchlist,
      result: await listScannerWatchlistItems(watchlist.id, true),
    })),
  );
  return results.map(({ watchlist, result }) => ({
    watchlist,
    items: readResult(`${watchlist.name} items`, result, [], failures),
  }));
}

async function loadSignals(
  signalIds: string[],
  failures: ScannerData["failures"],
): Promise<SignalClassification[]> {
  const uniqueIds = Array.from(new Set(signalIds)).slice(0, 20);
  const results = await Promise.all(
    uniqueIds.map(async (signalId) => ({
      signalId,
      result: await getSignal(signalId),
    })),
  );
  return results.flatMap(({ signalId, result }) => {
    if (result.ok) {
      return [result.data];
    }
    failures.push(scannerFailure(`Scan signal ${signalId}`, result));
    return [];
  });
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: ScannerData["failures"],
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
  failures: ScannerData["failures"],
): T | null {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return null;
}

function toFailure(label: string, result: ApiFailure): ScannerData["failures"][number] {
  return scannerFailure(label, result);
}
