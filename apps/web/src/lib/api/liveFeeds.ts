import { apiGet } from "./client";
import type { ApiResult, UUID } from "./types";
import type { LiveSubscription } from "@/lib/data-onboarding/types";

export function listLiveSubscriptions(params: {
  workspaceId: UUID;
  symbolId?: UUID;
}): Promise<ApiResult<LiveSubscription[]>> {
  return apiGet<LiveSubscription[]>("/live/subscriptions", {
    query: {
      workspace_id: params.workspaceId,
      symbol_id: params.symbolId,
      limit: 100,
    },
    optional: true,
  });
}
