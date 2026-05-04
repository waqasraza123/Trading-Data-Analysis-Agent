import { apiPostJson } from "./postClient";
import type { ApiResult, UUID } from "./types";
import type { DataQualityRun } from "@/lib/data-onboarding/types";

export function runCandleRangeQuality(params: {
  workspaceId: UUID;
  symbolId: UUID;
  sourceId?: UUID | null;
  timeframe: string;
  startTime: string;
  endTime: string;
}): Promise<ApiResult<DataQualityRun>> {
  return apiPostJson<DataQualityRun>(
    "/data-quality/candle-range/run",
    {
      workspace_id: params.workspaceId,
      symbol_id: params.symbolId,
      source_id: params.sourceId || null,
      timeframe: params.timeframe,
      start_time: params.startTime,
      end_time: params.endTime,
    },
    {
      optional: true,
      timeoutMs: 10000,
    },
  );
}
