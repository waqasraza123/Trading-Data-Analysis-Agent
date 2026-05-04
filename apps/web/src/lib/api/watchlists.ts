import { apiGet } from "./client";
import type { ApiResult, ScheduledScanConfig, UUID, Watchlist, WatchlistItem } from "./types";

export function listWatchlists(workspaceId: UUID): Promise<ApiResult<Watchlist[]>> {
  return apiGet<Watchlist[]>("/market-watchlists", {
    query: {
      workspace_id: workspaceId,
      status: "active",
      limit: 100,
    },
    optional: true,
  });
}

export function listWatchlistItems(watchlistId: UUID): Promise<ApiResult<WatchlistItem[]>> {
  return apiGet<WatchlistItem[]>(`/market-watchlists/${watchlistId}/items`, {
    query: {
      is_active: true,
      limit: 200,
    },
    optional: true,
  });
}

export function listScheduledScanConfigs(
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

export function listDueScheduledScanConfigs(
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
