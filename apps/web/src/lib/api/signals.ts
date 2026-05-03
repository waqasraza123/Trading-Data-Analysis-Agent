import { apiGet } from "./client";
import type { ApiResult, ContextRead, SignalClassification, UUID } from "./types";

export function getSignal(signalId: UUID): Promise<ApiResult<SignalClassification>> {
  return apiGet<SignalClassification>(`/signals/${signalId}`, { optional: true });
}

export function getAnalysisRunSignal(analysisRunId: UUID): Promise<ApiResult<SignalClassification>> {
  return apiGet<SignalClassification>(`/analysis-runs/${analysisRunId}/signal`, {
    optional: true,
  });
}

export function getSignalMarketRegime(signalId: UUID): Promise<ApiResult<ContextRead>> {
  return apiGet<ContextRead>(`/signals/${signalId}/market-regime`, { optional: true });
}

export function getSignalMarketSession(signalId: UUID): Promise<ApiResult<ContextRead>> {
  return apiGet<ContextRead>(`/signals/${signalId}/market-session`, { optional: true });
}
