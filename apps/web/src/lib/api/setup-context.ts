import { apiGet } from "./client";
import type { ApiResult, SetupContext, UUID } from "./types";

export function getSignalSetupContext(signalId: UUID): Promise<ApiResult<SetupContext>> {
  return apiGet<SetupContext>(`/signals/${signalId}/setup-context`, {
    optional: true,
  });
}

export function getAnalysisRunSetupContext(analysisRunId: UUID): Promise<ApiResult<SetupContext>> {
  return apiGet<SetupContext>(`/analysis-runs/${analysisRunId}/setup-context`, {
    optional: true,
  });
}
