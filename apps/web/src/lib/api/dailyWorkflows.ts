import { apiGet, apiPost } from "./client";
import type { ApiFailure, ApiResult, UUID } from "./types";
import type {
  DailyWorkflowFailure,
  DailyWorkflowRun,
  DailyWorkflowRunRequest,
  DailyWorkflowStep,
} from "@/lib/daily-workflows/types";

export function runDailyWorkflow(input: DailyWorkflowRunRequest): Promise<ApiResult<DailyWorkflowRun>> {
  return apiPost<DailyWorkflowRun>("/daily-workflows/run", input, {
    optional: true,
    timeoutMs: 120000,
  });
}

export function listDailyWorkflowRuns(params: {
  workspaceId: UUID;
  workflowType?: string;
  watchlistId?: UUID;
  limit?: number;
}): Promise<ApiResult<DailyWorkflowRun[]>> {
  return apiGet<DailyWorkflowRun[]>("/daily-workflows/runs", {
    query: {
      workspace_id: params.workspaceId,
      workflow_type: params.workflowType,
      watchlist_id: params.watchlistId,
      limit: params.limit || 10,
    },
    optional: true,
  });
}

export function getDailyWorkflowRun(runId: UUID): Promise<ApiResult<DailyWorkflowRun>> {
  return apiGet<DailyWorkflowRun>(`/daily-workflows/runs/${runId}`, { optional: true });
}

export function listDailyWorkflowSteps(runId: UUID): Promise<ApiResult<DailyWorkflowStep[]>> {
  return apiGet<DailyWorkflowStep[]>(`/daily-workflows/runs/${runId}/steps`, {
    optional: true,
  });
}

export function cancelDailyWorkflowRun(runId: UUID): Promise<ApiResult<DailyWorkflowRun>> {
  return apiPost<DailyWorkflowRun>(`/daily-workflows/runs/${runId}/cancel`, undefined, {
    optional: true,
  });
}

export function dailyWorkflowFailure(label: string, result: ApiFailure): DailyWorkflowFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}
