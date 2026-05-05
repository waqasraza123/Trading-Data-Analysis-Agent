import { getPublicEnv } from "@/config/env";
import { apiGet, apiPost } from "@/lib/api/client";
import { listJournalEntries } from "@/lib/api/journal";
import { listSignalOutcomes } from "@/lib/api/outcomes";
import { getLatestSignalReadiness } from "@/lib/api/readiness";
import { getSignalAuditTimeline, getSignalReport } from "@/lib/api/reports";
import { getSignal, getSignalMarketRegime, getSignalMarketSession } from "@/lib/api/signals";
import { getSetupChartContext } from "@/lib/api/setupChart";
import { getSignalSetupContext } from "@/lib/api/setup-context";
import type {
  ApiFailure,
  ApiResult,
  CrossAssetContextResult,
  CrossAssetContextRun,
  HistoricalCaseSearchRead,
  IntelligenceQualityResponse,
  MultiTimeframeContext,
  ScenarioReasoningResponse,
  UUID,
} from "@/lib/api/types";
import type { SetupDetailData, SetupDetailFailure } from "@/lib/setup-detail/types";

export async function getSetupDetail(signalId: UUID): Promise<SetupDetailData> {
  const env = getPublicEnv();
  const failures: SetupDetailFailure[] = [];
  const [
    reportResult,
    signalResult,
    outcomesResult,
    readinessResult,
    regimeResult,
    sessionResult,
    timelineResult,
    setupContextResult,
    qualityResult,
    reasoningResult,
    multiTimeframeResult,
    crossAssetResult,
  ] = await Promise.all([
    getSignalReport(signalId),
    getSignal(signalId),
    listSignalOutcomes(signalId),
    getLatestSignalReadiness(signalId),
    getSignalMarketRegime(signalId),
    getSignalMarketSession(signalId),
    getSignalAuditTimeline(signalId),
    getSignalSetupContext(signalId),
    getLatestSignalQuality(signalId),
    getLatestSignalReasoning(signalId),
    getSignalMultiTimeframeContext(signalId),
    getSignalCrossAssetContext(signalId),
  ]);

  const report = readNullableResult("Intelligence report", reportResult, failures);
  const signal = readNullableResult("Signal", signalResult, failures);
  const outcomes = readResult("Outcome history", outcomesResult, [], failures);
  const readiness = readNullableResult("Decision readiness", readinessResult, failures);
  const marketRegime = readNullableResult("Market regime", regimeResult, failures);
  const marketSession = readNullableResult("Market session", sessionResult, failures);
  const auditTimeline = readNullableResult("Audit timeline", timelineResult, failures);
  const setupContext = readNullableResult("Setup context", setupContextResult, failures);
  const quality = readNullableResult("Quality gates", qualityResult, failures);
  const reasoning = readNullableResult("Scenario reasoning", reasoningResult, failures);
  const multiTimeframeContext = readNullableResult("Multi-timeframe context", multiTimeframeResult, failures);
  const crossAssetContext = readNullableResult("Cross-asset context", crossAssetResult, failures);
  const workspaceId = signal?.signal.workspace_id || report?.workspace_id || setupContext?.workspace_id || null;
  const [historicalCasesResult, journalEntriesResult, crossAssetResultsResult] = await Promise.all([
    workspaceId ? searchHistoricalCases(signalId, workspaceId, signal?.signal) : null,
    workspaceId ? listJournalEntries({ workspaceId, signalId }) : null,
    crossAssetContext ? listCrossAssetContextResults(crossAssetContext.id) : null,
  ]);
  const setupChart = await getSetupChartContext({
    signalId,
    signal,
    setupContext,
    outcomes,
  });

  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    signalId,
    signal,
    report,
    setupContext,
    outcomes,
    readiness,
    marketRegime,
    marketSession,
    auditTimeline,
    quality,
    historicalCases: historicalCasesResult
      ? readNullableResult("Historical similar cases", historicalCasesResult, failures)
      : null,
    reasoning,
    multiTimeframeContext,
    crossAssetContext,
    crossAssetResults: crossAssetResultsResult
      ? readResult("Cross-asset context results", crossAssetResultsResult, [], failures)
      : [],
    journalEntries: journalEntriesResult
      ? readResult("Journal entries", journalEntriesResult, [], failures)
      : [],
    setupChart,
    failures,
    lastUpdatedAt: new Date().toISOString(),
  };
}

function getLatestSignalQuality(signalId: UUID): Promise<ApiResult<IntelligenceQualityResponse>> {
  return apiGet<IntelligenceQualityResponse>(`/intelligence-quality/signals/${signalId}/latest`, {
    optional: true,
  });
}

function getLatestSignalReasoning(signalId: UUID): Promise<ApiResult<ScenarioReasoningResponse>> {
  return apiGet<ScenarioReasoningResponse>(`/signals/${signalId}/reasoning/scenarios/latest`, {
    optional: true,
  });
}

function getSignalMultiTimeframeContext(signalId: UUID): Promise<ApiResult<MultiTimeframeContext>> {
  return apiGet<MultiTimeframeContext>(`/signals/${signalId}/multi-timeframe-context`, {
    optional: true,
  });
}

function getSignalCrossAssetContext(signalId: UUID): Promise<ApiResult<CrossAssetContextRun>> {
  return apiGet<CrossAssetContextRun>(`/signals/${signalId}/cross-asset-context`, {
    optional: true,
  });
}

function listCrossAssetContextResults(runId: UUID): Promise<ApiResult<CrossAssetContextResult[]>> {
  return apiGet<CrossAssetContextResult[]>(`/cross-asset-context/runs/${runId}/results`, {
    query: {
      limit: 25,
      offset: 0,
    },
    optional: true,
  });
}

function searchHistoricalCases(
  signalId: UUID,
  workspaceId: UUID,
  signal: { symbol_id: UUID; timeframe: string; strategy_profile_key: string | null; pattern_type: string | null; bias: string } | undefined,
): Promise<ApiResult<HistoricalCaseSearchRead>> {
  return apiPost<HistoricalCaseSearchRead>(
    `/signals/${signalId}/historical-cases/search`,
    {
      filters: {
        workspaceId,
        symbolId: signal?.symbol_id,
        timeframe: signal?.timeframe,
        strategyProfileKey: signal?.strategy_profile_key,
        patternType: signal?.pattern_type,
        bias: signal?.bias,
        includeOutcomes: true,
        excludeSameSignal: true,
      },
      limit: 5,
    },
    { optional: true },
  );
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: SetupDetailFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return fallback;
}

function readNullableResult<T>(
  label: string,
  result: ApiResult<T>,
  failures: SetupDetailFailure[],
): T | null {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return null;
}

function toFailure(label: string, result: ApiFailure): SetupDetailFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.missing ? "Endpoint not available yet" : result.error.message,
    missing: result.error.missing,
  };
}
