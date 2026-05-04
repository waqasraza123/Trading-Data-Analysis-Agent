import { apiGet } from "./client";
import type { ApiResult, SignalPriorityScore, UUID } from "./types";

export function getSignalPriorityScore(signalId: UUID): Promise<ApiResult<SignalPriorityScore>> {
  return apiGet<SignalPriorityScore>(`/signals/${signalId}/priority-score`, {
    optional: true,
  });
}
