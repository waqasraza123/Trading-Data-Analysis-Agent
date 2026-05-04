import { apiGet } from "./client";
import type { ActionItem, ApiResult, HealthResponse, UUID, WorkerStatusResponse } from "./types";

export function getApiHealth(): Promise<ApiResult<HealthResponse>> {
  return apiGet<HealthResponse>("/health", { optional: true, timeoutMs: 4000 });
}

export function getWorkerStatus(): Promise<ApiResult<WorkerStatusResponse>> {
  return apiGet<WorkerStatusResponse>("/health/workers", { optional: true, timeoutMs: 5000 });
}

export function listDueActionItems(workspaceId: UUID): Promise<ApiResult<ActionItem[]>> {
  return apiGet<ActionItem[]>("/action-items/due", {
    query: {
      workspace_id: workspaceId,
      limit: 100,
    },
    optional: true,
  });
}
