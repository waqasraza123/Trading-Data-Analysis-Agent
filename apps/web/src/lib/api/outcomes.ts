import { apiGet } from "./client";
import type { ApiResult, SignalOutcome, UUID } from "./types";

export function listSignalOutcomes(signalId: UUID): Promise<ApiResult<SignalOutcome[]>> {
  return apiGet<SignalOutcome[]>(`/signals/${signalId}/outcomes`, { optional: true });
}
