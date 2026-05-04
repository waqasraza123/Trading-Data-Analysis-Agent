import { apiGet } from "./client";
import type { ApiResult, UUID } from "./types";
import type { CandleCountRead, CandleQualityReport, CandleRead } from "@/lib/data-onboarding/types";

type CandleWindowParams = {
  workspaceId: UUID;
  symbolId: UUID;
  timeframe: string;
  sourceId?: UUID | null;
  startTime: string;
  endTime: string;
};

type LatestCandleParams = {
  workspaceId: UUID;
  symbolId: UUID;
  timeframe: string;
  sourceId?: UUID | null;
  isFinal?: boolean;
};

export function getLatestCandle(params: LatestCandleParams): Promise<ApiResult<CandleRead>> {
  return apiGet<CandleRead>("/candles/latest", {
    query: {
      workspace_id: params.workspaceId,
      symbol_id: params.symbolId,
      source_id: params.sourceId || undefined,
      timeframe: params.timeframe,
      is_final: params.isFinal ?? true,
    },
    optional: true,
  });
}

export function countCandles(params: CandleWindowParams): Promise<ApiResult<CandleCountRead>> {
  return apiGet<CandleCountRead>("/candles/count", {
    query: {
      workspace_id: params.workspaceId,
      symbol_id: params.symbolId,
      source_id: params.sourceId || undefined,
      timeframe: params.timeframe,
      start_time: params.startTime,
      end_time: params.endTime,
      is_final: true,
    },
    optional: true,
  });
}

export function getCandleQuality(params: CandleWindowParams): Promise<ApiResult<CandleQualityReport>> {
  return apiGet<CandleQualityReport>("/candles/quality", {
    query: {
      workspace_id: params.workspaceId,
      symbol_id: params.symbolId,
      source_id: params.sourceId || undefined,
      timeframe: params.timeframe,
      start_time: params.startTime,
      end_time: params.endTime,
    },
    optional: true,
  });
}
