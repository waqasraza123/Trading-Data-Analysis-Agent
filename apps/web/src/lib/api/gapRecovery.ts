import { apiGet } from "./client";
import { apiPostJson } from "./postClient";
import type {
  ApiResult,
  UUID,
} from "./types";
import type {
  CandleGapRecoveryItem,
  CandleGapRecoveryPlan,
  PrepareProviderPollingResponse,
} from "@/lib/data-onboarding/types";

export function createCandleGapRecoveryPlan(payload: {
  workspace_id: UUID;
  symbol_id: UUID;
  source_id: UUID | null;
  timeframe: string;
  start_time: string;
  end_time: string;
}): Promise<ApiResult<CandleGapRecoveryPlan>> {
  return apiPostJson<CandleGapRecoveryPlan>("/candle-gap-recovery/plans", payload, {
    optional: true,
    timeoutMs: 10000,
  });
}

export function listCandleGapRecoveryItems(
  planId: UUID,
): Promise<ApiResult<CandleGapRecoveryItem[]>> {
  return apiGet<CandleGapRecoveryItem[]>(`/candle-gap-recovery/plans/${planId}/items`, {
    query: {
      limit: 500,
    },
    optional: true,
  });
}

export function prepareProviderPollingRequests(
  planId: UUID,
  createRequests = false,
): Promise<ApiResult<PrepareProviderPollingResponse>> {
  return apiPostJson<PrepareProviderPollingResponse>(
    `/candle-gap-recovery/plans/${planId}/prepare-provider-polling`,
    {
      create_requests: createRequests,
    },
    {
      optional: true,
      timeoutMs: 10000,
    },
  );
}
