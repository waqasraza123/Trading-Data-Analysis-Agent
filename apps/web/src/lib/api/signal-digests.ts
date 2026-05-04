import { apiGet } from "./client";
import type { ApiResult, SignalDigestItem, SignalDigestRun, UUID } from "./types";

export function listSignalDigests(workspaceId: UUID): Promise<ApiResult<SignalDigestRun[]>> {
  return apiGet<SignalDigestRun[]>("/signal-digests", {
    optional: true,
    query: {
      workspaceId,
      limit: 5,
    },
  });
}

export function listSignalDigestItems(digestId: UUID): Promise<ApiResult<SignalDigestItem[]>> {
  return apiGet<SignalDigestItem[]>(`/signal-digests/${digestId}/items`, {
    optional: true,
    query: {
      limit: 25,
    },
  });
}
