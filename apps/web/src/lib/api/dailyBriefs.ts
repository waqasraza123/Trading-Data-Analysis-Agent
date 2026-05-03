import { apiGet } from "./client";
import type { ApiResult, DailyBriefItem, DailyBriefRun, UUID } from "./types";

export function getLatestWorkspaceDailyBrief(params: {
  workspaceId: UUID;
  briefType?: string;
  watchlistId?: UUID | null;
}): Promise<ApiResult<DailyBriefRun>> {
  return apiGet<DailyBriefRun>(`/workspaces/${params.workspaceId}/daily-brief/latest`, {
    optional: true,
    query: {
      briefType: params.briefType || "daily",
      watchlistId: params.watchlistId || undefined,
    },
  });
}

export function listDailyBriefItems(briefId: UUID): Promise<ApiResult<DailyBriefItem[]>> {
  return apiGet<DailyBriefItem[]>(`/daily-briefs/${briefId}/items`, {
    optional: true,
    query: {
      limit: 150,
    },
  });
}
