import { getPublicEnv } from "@/config/env";
import { apiDelete, apiGet, apiPost } from "./client";
import {
  getEquityDataOperationAuditBundle,
  getEquityDataOperationReviewQueue,
  getEquityDataOperationSummary,
  getLatestEquityFundamentals,
  getLatestEquityMetadata,
  listEquityDataOperations,
  listEquityDataProviderRequests,
  listEquityDataProviders,
  listEquityEarnings,
} from "./equityData";
import { listSymbols, listWorkspaces } from "./market";
import { listProviderCredentialRefs } from "./providerCredentials";
import type { ApiResult, UUID } from "./types";
import type {
  EquityCatalystContext,
  EquityCatalystCreateInput,
  EquityResearchData,
  EquityResearchFailure,
  EquitySwingCandidate,
  EquitySwingScanInput,
  EquitySwingScanRun,
  EquityUniverse,
  EquityUniverseCreateInput,
  EquityUniverseMember,
  EquityUniverseMemberCreateInput,
} from "@/lib/equity-research/types";
import { equityFailure } from "@/lib/equity-research/types";
import { equityDataFailure, type EquityDataFailure } from "@/lib/equity-data/types";

export function listEquityUniverses(workspaceId: UUID): Promise<ApiResult<EquityUniverse[]>> {
  return apiGet<EquityUniverse[]>("/equity-research/universes", {
    query: {
      workspace_id: workspaceId,
      limit: 100,
    },
    optional: true,
  });
}

export function createEquityUniverse(
  input: EquityUniverseCreateInput,
): Promise<ApiResult<EquityUniverse>> {
  return apiPost<EquityUniverse>("/equity-research/universes", input, { optional: true });
}

export function listEquityUniverseMembers(
  universeId: UUID,
): Promise<ApiResult<EquityUniverseMember[]>> {
  return apiGet<EquityUniverseMember[]>(`/equity-research/universes/${universeId}/members`, {
    query: {
      is_active: true,
      limit: 500,
    },
    optional: true,
  });
}

export function addEquityUniverseMember(
  universeId: UUID,
  input: EquityUniverseMemberCreateInput,
): Promise<ApiResult<EquityUniverseMember>> {
  return apiPost<EquityUniverseMember>(
    `/equity-research/universes/${universeId}/members`,
    input,
    { optional: true },
  );
}

export function removeEquityUniverseMember(
  universeId: UUID,
  memberId: UUID,
): Promise<ApiResult<EquityUniverseMember>> {
  return apiDelete<EquityUniverseMember>(
    `/equity-research/universes/${universeId}/members/${memberId}`,
    { optional: true },
  );
}

export function runEquitySwingScan(
  input: EquitySwingScanInput,
): Promise<ApiResult<EquitySwingScanRun>> {
  return apiPost<EquitySwingScanRun>("/equity-research/swing-scans", input, {
    optional: true,
    timeoutMs: 60000,
  });
}

export function listEquitySwingScans(
  workspaceId: UUID,
): Promise<ApiResult<EquitySwingScanRun[]>> {
  return apiGet<EquitySwingScanRun[]>("/equity-research/swing-scans", {
    query: {
      workspace_id: workspaceId,
      limit: 50,
    },
    optional: true,
  });
}

export function getEquitySwingScan(
  scanRunId: UUID,
): Promise<ApiResult<EquitySwingScanRun>> {
  return apiGet<EquitySwingScanRun>(`/equity-research/swing-scans/${scanRunId}`, {
    optional: true,
  });
}

export function listEquitySwingCandidates(
  scanRunId: UUID,
): Promise<ApiResult<EquitySwingCandidate[]>> {
  return apiGet<EquitySwingCandidate[]>(
    `/equity-research/swing-scans/${scanRunId}/candidates`,
    {
      query: { limit: 500 },
      optional: true,
    },
  );
}

export function getEquityCandidate(
  candidateId: UUID,
): Promise<ApiResult<EquitySwingCandidate>> {
  return apiGet<EquitySwingCandidate>(`/equity-research/candidates/${candidateId}`, {
    optional: true,
  });
}

export function createEquityCatalyst(
  input: EquityCatalystCreateInput,
): Promise<ApiResult<EquityCatalystContext>> {
  return apiPost<EquityCatalystContext>("/equity-research/catalysts", input, {
    optional: true,
  });
}

export function listEquityCatalysts(
  workspaceId: UUID,
  symbolId?: UUID,
): Promise<ApiResult<EquityCatalystContext[]>> {
  return apiGet<EquityCatalystContext[]>("/equity-research/catalysts", {
    query: {
      workspace_id: workspaceId,
      symbol_id: symbolId,
      limit: 100,
    },
    optional: true,
  });
}

export async function getEquityResearchData(params: {
  workspaceId?: string;
  universeId?: string;
  scanRunId?: string;
  candidateId?: string;
  operationId?: string;
}): Promise<EquityResearchData> {
  const env = getPublicEnv();
  const failures: EquityResearchFailure[] = [];
  const [workspacesResult, symbolsResult] = await Promise.all([listWorkspaces(), listSymbols()]);
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const symbols = readResult("Symbols", symbolsResult, [], failures);
  const stockSymbols = symbols.filter((symbol) => symbol.market_type === "stock");
  const workspace =
    workspaces.find((candidate) => candidate.id === params.workspaceId) || workspaces[0] || null;
  if (!workspace) {
    return emptyEquityData(env.appName, env.apiBaseUrl, params.workspaceId || null, failures);
  }
  const [
    universesResult,
    runsResult,
    catalystsResult,
    providersResult,
    requestsResult,
    operationsResult,
    operationSummaryResult,
    operationReviewQueueResult,
    credentialsResult,
  ] = await Promise.all([
    listEquityUniverses(workspace.id),
    listEquitySwingScans(workspace.id),
    listEquityCatalysts(workspace.id),
    listEquityDataProviders(),
    listEquityDataProviderRequests(workspace.id),
    listEquityDataOperations(workspace.id),
    getEquityDataOperationSummary(workspace.id),
    getEquityDataOperationReviewQueue(workspace.id),
    listProviderCredentialRefs(workspace.id),
  ]);
  const universes = readResult("Equity universes", universesResult, [], failures);
  const scanRuns = readResult("Equity swing scans", runsResult, [], failures);
  const selectedUniverse =
    universes.find((universe) => universe.id === params.universeId) || universes[0] || null;
  const selectedScanRun =
    scanRuns.find((run) => run.id === params.scanRunId) || scanRuns[0] || null;
  const [membersResult, candidatesResult] = await Promise.all([
    selectedUniverse
      ? listEquityUniverseMembers(selectedUniverse.id)
      : Promise.resolve<ApiResult<EquityUniverseMember[]>>({
          ok: true,
          status: 200,
          url: "",
          data: [],
        }),
    selectedScanRun
      ? listEquitySwingCandidates(selectedScanRun.id)
      : Promise.resolve<ApiResult<EquitySwingCandidate[]>>({
          ok: true,
          status: 200,
          url: "",
          data: [],
        }),
  ]);
  const selectedUniverseMembers = readResult("Universe members", membersResult, [], failures);
  const candidates = readResult("Swing candidates", candidatesResult, [], failures);
  const selectedCandidate =
    candidates.find((candidate) => candidate.id === params.candidateId) || candidates[0] || null;
  const selectedSymbolId =
    selectedCandidate?.symbol_id || selectedUniverseMembers[0]?.symbol_id || stockSymbols[0]?.id || null;
  const [
    metadataResult,
    fundamentalsResult,
    earningsResult,
    operationAuditBundleResult,
  ] = await Promise.all([
    selectedSymbolId
      ? getLatestEquityMetadata(workspace.id, selectedSymbolId)
      : emptyResult(null),
    selectedSymbolId
      ? getLatestEquityFundamentals(workspace.id, selectedSymbolId)
      : emptyResult(null),
    selectedSymbolId ? listEquityEarnings(workspace.id, selectedSymbolId) : emptyResult([]),
    params.operationId ? getEquityDataOperationAuditBundle(params.operationId) : emptyResult(null),
  ]);
  const equityDataFailures: EquityDataFailure[] = [];
  const selectedOperationAuditBundle = readEquityDataResult(
    "Equity data operation audit bundle",
    operationAuditBundleResult,
    null,
    equityDataFailures,
  );
  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    requestedWorkspaceId: params.workspaceId || null,
    workspace,
    workspaces,
    stockSymbols,
    universes,
    selectedUniverse,
    selectedUniverseMembers,
    scanRuns,
    selectedScanRun,
    candidates,
    selectedCandidate,
    catalysts: readResult("Catalysts", catalystsResult, [], failures),
    equityDataProviders: readEquityDataResult(
      "Equity data providers",
      providersResult,
      [],
      equityDataFailures,
    ),
    providerRequests: readEquityDataResult(
      "Equity data requests",
      requestsResult,
      [],
      equityDataFailures,
    ),
    operations: readEquityDataResult(
      "Equity data operations",
      operationsResult,
      { operations: [] },
      equityDataFailures,
    ).operations,
    operationSummary: readEquityDataResult(
      "Equity data operation summary",
      operationSummaryResult,
      null,
      equityDataFailures,
    ),
    operationReviewQueue: readEquityDataResult(
      "Equity data operation review queue",
      operationReviewQueueResult,
      null,
      equityDataFailures,
    ),
    selectedOperationAuditBundle,
    selectedOperation: selectedOperationAuditBundle?.operation ?? null,
    selectedOperationDiagnostics: selectedOperationAuditBundle?.diagnostics ?? null,
    selectedOperationLineage: selectedOperationAuditBundle?.lineage ?? null,
    selectedMetadata: readEquityDataResult(
      "Symbol metadata",
      metadataResult,
      null,
      equityDataFailures,
    ),
    selectedFundamentals: readEquityDataResult(
      "Fundamentals context",
      fundamentalsResult,
      null,
      equityDataFailures,
    ),
    selectedEarnings: readEquityDataResult(
      "Earnings context",
      earningsResult,
      [],
      equityDataFailures,
    ),
    providerCredentialRefs: readEquityDataResult(
      "Provider credential refs",
      credentialsResult,
      [],
      equityDataFailures,
    ),
    equityDataFailures,
    failures,
    lastUpdatedAt: new Date().toISOString(),
  };
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: EquityResearchFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(equityFailure(label, result));
  return fallback;
}

function emptyEquityData(
  appName: string,
  apiBaseUrl: string,
  requestedWorkspaceId: UUID | null,
  failures: EquityResearchFailure[],
): EquityResearchData {
  return {
    appName,
    apiBaseUrl,
    requestedWorkspaceId,
    workspace: null,
    workspaces: [],
    stockSymbols: [],
    universes: [],
    selectedUniverse: null,
    selectedUniverseMembers: [],
    scanRuns: [],
    selectedScanRun: null,
    candidates: [],
    selectedCandidate: null,
    catalysts: [],
    equityDataProviders: [],
    providerRequests: [],
    operations: [],
    operationSummary: null,
    operationReviewQueue: null,
    selectedOperationAuditBundle: null,
    selectedOperation: null,
    selectedOperationDiagnostics: null,
    selectedOperationLineage: null,
    selectedMetadata: null,
    selectedFundamentals: null,
    selectedEarnings: [],
    providerCredentialRefs: [],
    equityDataFailures: [],
    failures,
    lastUpdatedAt: new Date().toISOString(),
  };
}

function readEquityDataResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: EquityDataFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(equityDataFailure(label, result));
  return fallback;
}

function emptyResult<T>(data: T): Promise<ApiResult<T>> {
  return Promise.resolve({
    ok: true,
    status: 200,
    url: "",
    data,
  });
}
