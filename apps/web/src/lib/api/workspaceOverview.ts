import { apiGet } from "./client";
import type { ApiResult, UUID } from "./types";
import type { WorkspaceOverview } from "@/lib/command-center/overviewTypes";

export type WorkspaceOverviewParams = {
  periodStart?: string | null;
  periodEnd?: string | null;
  watchlistId?: UUID | null;
  preferenceProfileId?: UUID | null;
  includeReadModels?: boolean;
  includeNotifications?: boolean;
  includeJournal?: boolean;
  includeQuality?: boolean;
};

export function getWorkspaceOverview(
  workspaceId: UUID,
  params: WorkspaceOverviewParams = {},
): Promise<ApiResult<WorkspaceOverview>> {
  return apiGet<WorkspaceOverview>(`/workspaces/${workspaceId}/overview`, {
    query: {
      periodStart: params.periodStart || undefined,
      periodEnd: params.periodEnd || undefined,
      watchlistId: params.watchlistId || undefined,
      preferenceProfileId: params.preferenceProfileId || undefined,
      includeReadModels: params.includeReadModels ?? true,
      includeNotifications: params.includeNotifications ?? true,
      includeJournal: params.includeJournal ?? true,
      includeQuality: params.includeQuality ?? true,
    },
    optional: true,
  });
}
