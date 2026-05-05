import { apiGet, apiPost } from "./client";
import type { ApiFailure, ApiResult, UUID } from "./types";
import type {
  DailyRoutineFailure,
  DailyRoutineRun,
  DailyRoutineRunRequest,
  DailyRoutineRunStep,
  DailyRoutineTemplate,
  DailyRoutineType,
} from "@/lib/routines/types";

export function listDailyRoutineTemplates(params: {
  workspaceId?: UUID;
  routineType?: DailyRoutineType;
} = {}): Promise<ApiResult<DailyRoutineTemplate[]>> {
  return apiGet<DailyRoutineTemplate[]>("/daily-routines/templates", {
    query: {
      workspace_id: params.workspaceId,
      routine_type: params.routineType,
      status: "active",
    },
    optional: true,
  });
}

export function runDailyRoutineTemplate(
  templateId: UUID,
  input: DailyRoutineRunRequest,
): Promise<ApiResult<DailyRoutineRun>> {
  return apiPost<DailyRoutineRun>(`/daily-routines/templates/${templateId}/run`, input, {
    optional: true,
    timeoutMs: 120000,
  });
}

export function listDailyRoutineRuns(params: {
  workspaceId: UUID;
  templateId?: UUID;
  limit?: number;
}): Promise<ApiResult<DailyRoutineRun[]>> {
  return apiGet<DailyRoutineRun[]>("/daily-routines/runs", {
    query: {
      workspace_id: params.workspaceId,
      template_id: params.templateId,
      limit: params.limit || 10,
    },
    optional: true,
  });
}

export function getDailyRoutineRun(runId: UUID): Promise<ApiResult<DailyRoutineRun>> {
  return apiGet<DailyRoutineRun>(`/daily-routines/runs/${runId}`, { optional: true });
}

export function listDailyRoutineRunSteps(runId: UUID): Promise<ApiResult<DailyRoutineRunStep[]>> {
  return apiGet<DailyRoutineRunStep[]>(`/daily-routines/runs/${runId}/steps`, {
    optional: true,
  });
}

export function dailyRoutineFailure(label: string, result: ApiFailure): DailyRoutineFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}
