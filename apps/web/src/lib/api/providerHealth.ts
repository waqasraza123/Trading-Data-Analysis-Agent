import { apiGet, apiPost } from "./client";
import type { ApiResult, UUID } from "./types";
import type {
  ProviderHealthPrepareGapRecoveryResponse,
  ProviderHealthSnapshot,
  ProviderHealthSummary,
  ProviderHealthWorkspaceRefreshResponse,
} from "@/lib/provider-health/types";

export function listProviderHealthSnapshots(params: {
  workspaceId: UUID;
  sourceId?: UUID;
  symbolId?: UUID;
  timeframe?: string;
  status?: string;
}): Promise<ApiResult<ProviderHealthSnapshot[]>> {
  return apiGet<ProviderHealthSnapshot[]>("/provider-health/snapshots", {
    query: {
      workspace_id: params.workspaceId,
      source_id: params.sourceId,
      symbol_id: params.symbolId,
      timeframe: params.timeframe,
      status: params.status,
      limit: 500,
    },
    optional: true,
  });
}

export function getProviderHealthSummary(
  workspaceId: UUID,
): Promise<ApiResult<ProviderHealthSummary>> {
  return apiGet<ProviderHealthSummary>(`/provider-health/workspaces/${workspaceId}/summary`, {
    optional: true,
  });
}

export function refreshProviderHealthWorkspace(
  workspaceId: UUID,
): Promise<ApiResult<ProviderHealthWorkspaceRefreshResponse>> {
  return apiPost<ProviderHealthWorkspaceRefreshResponse>(
    `/provider-health/workspaces/${workspaceId}/refresh`,
    undefined,
    {
      query: { limit: 500 },
      optional: true,
      timeoutMs: 12000,
    },
  );
}

export function prepareProviderHealthGapRecovery(
  snapshotId: UUID,
  createRequests = false,
): Promise<ApiResult<ProviderHealthPrepareGapRecoveryResponse>> {
  return apiPost<ProviderHealthPrepareGapRecoveryResponse>(
    `/provider-health/snapshots/${snapshotId}/prepare-gap-recovery`,
    {
      create_requests: createRequests,
    },
    {
      optional: true,
      timeoutMs: 12000,
    },
  );
}
