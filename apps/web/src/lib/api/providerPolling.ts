import { apiGet } from "./client";
import type { ApiResult, UUID } from "./types";
import type { ProviderPollingRequest } from "@/lib/data-onboarding/types";

export function listProviderPollingRequests(params: {
  workspaceId: UUID;
  symbolId?: UUID;
  sourceId?: UUID;
}): Promise<ApiResult<ProviderPollingRequest[]>> {
  return apiGet<ProviderPollingRequest[]>("/provider-polling/requests", {
    query: {
      workspace_id: params.workspaceId,
      symbol_id: params.symbolId,
      source_id: params.sourceId,
      limit: 100,
    },
    optional: true,
  });
}
