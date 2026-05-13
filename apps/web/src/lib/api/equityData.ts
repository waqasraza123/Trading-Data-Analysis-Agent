import { apiGet, apiPost, apiPostForm } from "./client";
import type { ApiResult, UUID } from "./types";
import type {
  EquityDataProviderCapability,
  EquityDataOperation,
  EquityDataOperationAuditBundle,
  EquityDataOperationCancelInput,
  EquityDataOperationDetail,
  EquityDataOperationDiagnostics,
  EquityDataOperationInput,
  EquityDataOperationLineage,
  EquityDataOperationList,
  EquityDataOperationRetryInput,
  EquityDataOperationReviewQueue,
  EquityDataOperationSummary,
  EquityDataProviderRequest,
  EquityEarningsEvent,
  EquityFileImportResult,
  EquityFundamentalSnapshot,
  EquityProviderUniverseImportInput,
  EquitySymbolEnrichmentInput,
  EquitySymbolMetadataSnapshot,
  EquityUniverseRowsImportInput,
} from "@/lib/equity-data/types";

export function listEquityDataProviders(): Promise<ApiResult<EquityDataProviderCapability[]>> {
  return apiGet<EquityDataProviderCapability[]>("/equity-data/providers", { optional: true });
}

export function importEquityUniverseRows(
  input: EquityUniverseRowsImportInput,
): Promise<ApiResult<EquityDataProviderRequest>> {
  return apiPost<EquityDataProviderRequest>("/equity-data/universe-import/rows", input, {
    optional: true,
    timeoutMs: 30000,
  });
}

export function importEquityUniverseProvider(
  input: EquityProviderUniverseImportInput,
): Promise<ApiResult<EquityDataProviderRequest>> {
  return apiPost<EquityDataProviderRequest>("/equity-data/universe-import/provider", input, {
    optional: true,
    timeoutMs: 30000,
  });
}

export function listEquityDataProviderRequests(
  workspaceId: UUID,
): Promise<ApiResult<EquityDataProviderRequest[]>> {
  return apiGet<EquityDataProviderRequest[]>("/equity-data/provider-requests", {
    query: { workspace_id: workspaceId, limit: 25 },
    optional: true,
  });
}

export function listEquityDataOperations(
  workspaceId: UUID,
): Promise<ApiResult<EquityDataOperationList>> {
  return apiGet<EquityDataOperationList>("/equity-data/operations", {
    query: { workspace_id: workspaceId, limit: 25 },
    optional: true,
  });
}

export function getEquityDataOperationSummary(
  workspaceId: UUID,
): Promise<ApiResult<EquityDataOperationSummary>> {
  return apiGet<EquityDataOperationSummary>("/equity-data/operations/summary", {
    query: { workspace_id: workspaceId, problem_limit: 5 },
    optional: true,
  });
}

export function getEquityDataOperationReviewQueue(
  workspaceId: UUID,
): Promise<ApiResult<EquityDataOperationReviewQueue>> {
  return apiGet<EquityDataOperationReviewQueue>("/equity-data/operations/review-queue", {
    query: { workspace_id: workspaceId, limit: 8, stale_after_minutes: 30 },
    optional: true,
  });
}

export function getEquityDataOperation(
  operationId: UUID,
): Promise<ApiResult<EquityDataOperationDetail>> {
  return apiGet<EquityDataOperationDetail>(`/equity-data/operations/${operationId}`, {
    optional: true,
  });
}

export function getEquityDataOperationDiagnostics(
  operationId: UUID,
): Promise<ApiResult<EquityDataOperationDiagnostics>> {
  return apiGet<EquityDataOperationDiagnostics>(
    `/equity-data/operations/${operationId}/diagnostics`,
    { optional: true },
  );
}

export function getEquityDataOperationLineage(
  operationId: UUID,
): Promise<ApiResult<EquityDataOperationLineage>> {
  return apiGet<EquityDataOperationLineage>(
    `/equity-data/operations/${operationId}/lineage`,
    { optional: true },
  );
}

export function getEquityDataOperationAuditBundle(
  operationId: UUID,
): Promise<ApiResult<EquityDataOperationAuditBundle>> {
  return apiGet<EquityDataOperationAuditBundle>(
    `/equity-data/operations/${operationId}/audit-bundle`,
    { optional: true },
  );
}

export function cancelEquityDataOperation(
  operationId: UUID,
  input: EquityDataOperationCancelInput = {},
): Promise<ApiResult<EquityDataOperation>> {
  return apiPost<EquityDataOperation>(
    `/equity-data/operations/${operationId}/cancel`,
    input,
    { optional: true, timeoutMs: 15000 },
  );
}

export function retryEquityDataOperation(
  operationId: UUID,
  input: EquityDataOperationRetryInput = {},
): Promise<ApiResult<EquityDataOperation>> {
  return apiPost<EquityDataOperation>(
    `/equity-data/operations/${operationId}/retry`,
    input,
    { optional: true, timeoutMs: 30000 },
  );
}

export function queueEquityMetadataEnrichment(
  input: EquityDataOperationInput,
): Promise<ApiResult<EquityDataOperation>> {
  return apiPost<EquityDataOperation>("/equity-data/operations/metadata-enrichment", input, {
    optional: true,
    timeoutMs: 30000,
  });
}

export function queueEquityFundamentalsEnrichment(
  input: EquityDataOperationInput,
): Promise<ApiResult<EquityDataOperation>> {
  return apiPost<EquityDataOperation>("/equity-data/operations/fundamentals-enrichment", input, {
    optional: true,
    timeoutMs: 30000,
  });
}

export function queueEquityEarningsEnrichment(
  input: EquityDataOperationInput,
): Promise<ApiResult<EquityDataOperation>> {
  return apiPost<EquityDataOperation>("/equity-data/operations/earnings-enrichment", input, {
    optional: true,
    timeoutMs: 30000,
  });
}

export function queueEquityEarningsToCatalysts(
  input: Omit<EquityDataOperationInput, "provider" | "credentialRefId" | "filters">,
): Promise<ApiResult<EquityDataOperation>> {
  return apiPost<EquityDataOperation>("/equity-data/operations/earnings-to-catalysts", input, {
    optional: true,
    timeoutMs: 30000,
  });
}

export function importEquityUniverseFile(input: {
  workspaceId: UUID;
  file: File;
  universeId?: UUID;
  createUniverseName?: string;
  providerName?: string;
  runMode?: "sync" | "queued" | "auto";
  dryRun?: boolean;
}): Promise<ApiResult<EquityFileImportResult>> {
  const formData = new FormData();
  formData.set("workspace_id", input.workspaceId);
  formData.set("file", input.file);
  if (input.universeId) {
    formData.set("universe_id", input.universeId);
  }
  if (input.createUniverseName) {
    formData.set("create_universe_name", input.createUniverseName);
  }
  formData.set("provider_name", input.providerName || "csv_equity_import");
  formData.set("run_mode", input.runMode || "auto");
  formData.set("dry_run", input.dryRun ? "true" : "false");
  return apiPostForm<EquityFileImportResult>(
    "/equity-data/operations/universe-import-file",
    formData,
    { optional: true, timeoutMs: 60000 },
  );
}

export function lookupEquityMetadata(
  symbolId: UUID,
  input: EquitySymbolEnrichmentInput,
): Promise<ApiResult<EquityDataProviderRequest>> {
  return apiPost<EquityDataProviderRequest>(
    `/equity-data/symbols/${symbolId}/metadata/lookup`,
    input,
    { optional: true, timeoutMs: 30000 },
  );
}

export function getLatestEquityMetadata(
  workspaceId: UUID,
  symbolId: UUID,
): Promise<ApiResult<EquitySymbolMetadataSnapshot | null>> {
  return apiGet<EquitySymbolMetadataSnapshot | null>(
    `/equity-data/symbols/${symbolId}/metadata/latest`,
    { query: { workspace_id: workspaceId }, optional: true },
  );
}

export function fetchEquityFundamentals(
  symbolId: UUID,
  input: EquitySymbolEnrichmentInput,
): Promise<ApiResult<EquityDataProviderRequest>> {
  return apiPost<EquityDataProviderRequest>(
    `/equity-data/symbols/${symbolId}/fundamentals/fetch`,
    input,
    { optional: true, timeoutMs: 30000 },
  );
}

export function getLatestEquityFundamentals(
  workspaceId: UUID,
  symbolId: UUID,
): Promise<ApiResult<EquityFundamentalSnapshot | null>> {
  return apiGet<EquityFundamentalSnapshot | null>(
    `/equity-data/symbols/${symbolId}/fundamentals/latest`,
    { query: { workspace_id: workspaceId }, optional: true },
  );
}

export function fetchEquityEarnings(
  symbolId: UUID,
  input: EquitySymbolEnrichmentInput,
): Promise<ApiResult<EquityDataProviderRequest>> {
  return apiPost<EquityDataProviderRequest>(
    `/equity-data/symbols/${symbolId}/earnings/fetch`,
    input,
    { optional: true, timeoutMs: 30000 },
  );
}

export function listEquityEarnings(
  workspaceId: UUID,
  symbolId: UUID,
): Promise<ApiResult<EquityEarningsEvent[]>> {
  return apiGet<EquityEarningsEvent[]>(`/equity-data/symbols/${symbolId}/earnings`, {
    query: { workspace_id: workspaceId, limit: 20 },
    optional: true,
  });
}

export function createEarningsCatalystContext(
  eventId: UUID,
): Promise<ApiResult<unknown>> {
  return apiPost<unknown>(`/equity-data/earnings/${eventId}/create-catalyst-context`, {}, {
    optional: true,
  });
}
