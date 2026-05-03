import { apiGet } from "./client";
import type { ApiResult, DecisionReadinessAssessmentResponse, UUID } from "./types";

export function getLatestSignalReadiness(
  signalId: UUID,
): Promise<ApiResult<DecisionReadinessAssessmentResponse>> {
  return apiGet<DecisionReadinessAssessmentResponse>(
    `/decision-readiness/signals/${signalId}/latest`,
    { optional: true },
  );
}
