import { apiGet, apiPost } from "./client";
import type { ApiResult, UUID } from "./types";
import type {
  EquityDataProviderCapability,
  EquityDataProviderRequest,
  EquityEarningsEvent,
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
