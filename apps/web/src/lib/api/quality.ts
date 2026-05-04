import { getPublicEnv } from "@/config/env";
import { apiGet } from "@/lib/api/client";
import { listSymbols, listWorkspaces } from "@/lib/api/market";
import type { ApiFailure, ApiResult, UUID } from "@/lib/api/types";
import { composeQualityScoreboard, matchesQualityFilters, parseQualityFilters } from "@/lib/quality/composeQualityScoreboard";
import type {
  BacktestExperimentCohort,
  BacktestExperimentRun,
  CalibrationRecommendation,
  CohortDriftResult,
  ConfidenceCalibrationBin,
  ConfidenceCalibrationRun,
  OutcomePerformanceSummary,
  PatternAttributionResult,
  PatternAttributionRun,
  PatternOutcomeDiagnostic,
  QualityFailure,
  QualityFilters,
  QualityScoreboardData,
  StrategyProfileDiagnostic,
  StrategyProfileRead,
  WalkForwardValidationComparison,
  WalkForwardValidationRun,
  WalkForwardValidationWindow,
} from "@/lib/quality/types";
import { qualityFailure } from "@/lib/quality/types";

const defaultHorizonMinutes = 30;
const endpointNames = [
  "GET /workspaces",
  "GET /symbols",
  "GET /strategy-profiles",
  "GET /outcomes/performance/strategy-profiles",
  "GET /outcomes/performance/patterns",
  "GET /outcomes/performance/symbols",
  "GET /profile-diagnostics/strategy-profiles",
  "GET /profile-diagnostics/patterns",
  "GET /profile-diagnostics/recommendations",
  "GET /confidence-calibration/runs",
  "GET /confidence-calibration/runs/{runId}/bins",
  "GET /walk-forward-validations/runs",
  "GET /walk-forward-validations/runs/{runId}/windows",
  "GET /walk-forward-validations/runs/{runId}/comparisons",
  "GET /cohort-drift/results/recent",
  "GET /pattern-attribution/runs",
  "GET /pattern-attribution/runs/{runId}/results",
  "GET /backtest-experiments/runs",
  "GET /backtest-experiments/runs/{runId}/cohorts",
];

export async function getQualityScoreboardData(params: Record<string, string | undefined>): Promise<QualityScoreboardData> {
  const env = getPublicEnv();
  const filters = parseQualityFilters(params);
  const failures: QualityFailure[] = [];
  const [workspacesResult, symbolsResult, strategyProfilesResult] = await Promise.all([
    listWorkspaces(),
    listSymbols(),
    listStrategyProfiles(),
  ]);
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const symbols = readResult("Symbols", symbolsResult, [], failures);
  const strategyProfiles = readResult("Strategy profiles", strategyProfilesResult, [], failures);
  const workspace = workspaces.find((candidate) => candidate.id === filters.workspaceId) || workspaces[0] || null;

  if (!workspace) {
    return composeQualityScoreboard({
      data: {
        appName: env.appName,
        apiBaseUrl: env.apiBaseUrl,
        requestedWorkspaceId: filters.workspaceId || null,
        workspace: null,
        workspaces,
        symbols,
        strategyProfiles,
        filters,
        failures,
        endpoints: endpointNames,
        lastLoadedAt: new Date().toISOString(),
      },
      profilePerformance: [],
      patternPerformance: [],
      symbolPerformance: [],
      profileDiagnostics: [],
      patternDiagnostics: [],
      recommendations: [],
      calibrationBins: [],
      walkForwardWindows: [],
      walkForwardComparisons: [],
      cohortDrift: [],
      patternAttribution: [],
      backtestCohorts: [],
    });
  }

  const resolvedFilters = matchesQualityFilters(filters, workspace.id);
  const horizonMinutes = resolvedFilters.horizonMinutes || defaultHorizonMinutes;
  const [
    profilePerformanceResult,
    patternPerformanceResult,
    symbolPerformanceResult,
    profileDiagnosticsResult,
    patternDiagnosticsResult,
    recommendationsResult,
    calibrationRunsResult,
    walkForwardRunsResult,
    cohortDriftResult,
    patternAttributionRunsResult,
    backtestRunsResult,
  ] = await Promise.all([
    listProfilePerformance(workspace.id, resolvedFilters, horizonMinutes),
    listPatternPerformance(workspace.id, resolvedFilters, horizonMinutes),
    listSymbolPerformance(workspace.id, resolvedFilters, horizonMinutes),
    listProfileDiagnostics(workspace.id, resolvedFilters),
    listPatternDiagnostics(workspace.id, resolvedFilters),
    listCalibrationRecommendations(workspace.id, resolvedFilters),
    listConfidenceCalibrationRuns(workspace.id),
    listWalkForwardValidationRuns(workspace.id),
    listRecentCohortDrift(workspace.id, resolvedFilters),
    listPatternAttributionRuns(workspace.id),
    listBacktestExperimentRuns(workspace.id),
  ]);

  const profilePerformance = readOptionalResult("Profile outcome behavior", profilePerformanceResult, [], failures);
  const patternPerformance = readOptionalResult("Pattern outcome behavior", patternPerformanceResult, [], failures);
  const symbolPerformance = readOptionalResult("Symbol outcome behavior", symbolPerformanceResult, [], failures);
  const profileDiagnostics = readOptionalResult("Profile diagnostics", profileDiagnosticsResult, [], failures);
  const patternDiagnostics = readOptionalResult("Pattern diagnostics", patternDiagnosticsResult, [], failures);
  const recommendations = readOptionalResult("Calibration recommendations", recommendationsResult, [], failures);
  const calibrationRuns = readOptionalResult("Confidence calibration runs", calibrationRunsResult, [], failures);
  const walkForwardRuns = readOptionalResult("Walk-forward validation runs", walkForwardRunsResult, [], failures);
  const cohortDrift = readOptionalResult("Cohort drift", cohortDriftResult, [], failures);
  const patternAttributionRuns = readOptionalResult("Pattern attribution runs", patternAttributionRunsResult, [], failures);
  const backtestRuns = readOptionalResult("Backtest experiment runs", backtestRunsResult, [], failures);

  const latestCalibrationRun = calibrationRuns[0] || null;
  const latestWalkForwardRun = walkForwardRuns[0] || null;
  const latestPatternAttributionRun = patternAttributionRuns[0] || null;
  const latestBacktestRun = backtestRuns[0] || null;
  const [calibrationBinsResult, walkForwardWindowsResult, walkForwardComparisonsResult, patternAttributionResult, backtestCohortsResult] =
    await Promise.all([
      latestCalibrationRun ? listConfidenceCalibrationBins(latestCalibrationRun.id, resolvedFilters) : Promise.resolve(null),
      latestWalkForwardRun ? listWalkForwardValidationWindows(latestWalkForwardRun.id, resolvedFilters) : Promise.resolve(null),
      latestWalkForwardRun ? listWalkForwardValidationComparisons(latestWalkForwardRun.id) : Promise.resolve(null),
      latestPatternAttributionRun ? listPatternAttributionResults(latestPatternAttributionRun.id, resolvedFilters) : Promise.resolve(null),
      latestBacktestRun ? listBacktestExperimentCohorts(latestBacktestRun.id) : Promise.resolve(null),
    ]);

  const calibrationBins = calibrationBinsResult ? readOptionalResult("Confidence calibration bins", calibrationBinsResult, [], failures) : [];
  const walkForwardWindows = walkForwardWindowsResult ? readOptionalResult("Walk-forward windows", walkForwardWindowsResult, [], failures) : [];
  const walkForwardComparisons = walkForwardComparisonsResult ? readOptionalResult("Walk-forward comparisons", walkForwardComparisonsResult, [], failures) : [];
  const patternAttribution = patternAttributionResult ? readOptionalResult("Pattern attribution results", patternAttributionResult, [], failures) : [];
  const backtestCohorts = backtestCohortsResult ? readOptionalResult("Backtest experiment cohorts", backtestCohortsResult, [], failures) : [];

  return composeQualityScoreboard({
    data: {
      appName: env.appName,
      apiBaseUrl: env.apiBaseUrl,
      requestedWorkspaceId: filters.workspaceId || null,
      workspace,
      workspaces,
      symbols,
      strategyProfiles,
      filters: resolvedFilters,
      failures,
      endpoints: endpointNames,
      lastLoadedAt: new Date().toISOString(),
    },
    profilePerformance,
    patternPerformance,
    symbolPerformance,
    profileDiagnostics,
    patternDiagnostics,
    recommendations,
    calibrationBins,
    walkForwardWindows,
    walkForwardComparisons,
    cohortDrift,
    patternAttribution,
    backtestCohorts,
  });
}

function listStrategyProfiles(): Promise<ApiResult<StrategyProfileRead[]>> {
  return apiGet<StrategyProfileRead[]>("/strategy-profiles", {
    optional: true,
    query: {
      is_active: true,
      limit: 500,
    },
  });
}

function listProfilePerformance(
  workspaceId: UUID,
  filters: QualityFilters,
  horizonMinutes: number,
): Promise<ApiResult<OutcomePerformanceSummary[]>> {
  return apiGet<OutcomePerformanceSummary[]>("/outcomes/performance/strategy-profiles", {
    optional: true,
    query: performanceQuery(workspaceId, filters, horizonMinutes),
  });
}

function listPatternPerformance(
  workspaceId: UUID,
  filters: QualityFilters,
  horizonMinutes: number,
): Promise<ApiResult<OutcomePerformanceSummary[]>> {
  return apiGet<OutcomePerformanceSummary[]>("/outcomes/performance/patterns", {
    optional: true,
    query: performanceQuery(workspaceId, filters, horizonMinutes),
  });
}

function listSymbolPerformance(
  workspaceId: UUID,
  filters: QualityFilters,
  horizonMinutes: number,
): Promise<ApiResult<OutcomePerformanceSummary[]>> {
  return apiGet<OutcomePerformanceSummary[]>("/outcomes/performance/symbols", {
    optional: true,
    query: performanceQuery(workspaceId, filters, horizonMinutes),
  });
}

function listProfileDiagnostics(
  workspaceId: UUID,
  filters: QualityFilters,
): Promise<ApiResult<StrategyProfileDiagnostic[]>> {
  return apiGet<StrategyProfileDiagnostic[]>("/profile-diagnostics/strategy-profiles", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      strategy_profile_key: filters.strategyProfileKey,
      symbol_id: filters.symbolId,
      timeframe: filters.timeframe,
      horizon_minutes: filters.horizonMinutes,
      limit: 100,
    },
  });
}

function listPatternDiagnostics(
  workspaceId: UUID,
  filters: QualityFilters,
): Promise<ApiResult<PatternOutcomeDiagnostic[]>> {
  return apiGet<PatternOutcomeDiagnostic[]>("/profile-diagnostics/patterns", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      pattern_type: filters.patternType,
      strategy_profile_key: filters.strategyProfileKey,
      symbol_id: filters.symbolId,
      timeframe: filters.timeframe,
      horizon_minutes: filters.horizonMinutes,
      limit: 100,
    },
  });
}

function listCalibrationRecommendations(
  workspaceId: UUID,
  filters: QualityFilters,
): Promise<ApiResult<CalibrationRecommendation[]>> {
  return apiGet<CalibrationRecommendation[]>("/profile-diagnostics/recommendations", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      strategy_profile_key: filters.strategyProfileKey,
      pattern_type: filters.patternType,
      symbol_id: filters.symbolId,
      timeframe: filters.timeframe,
      limit: 100,
    },
  });
}

function listConfidenceCalibrationRuns(workspaceId: UUID): Promise<ApiResult<ConfidenceCalibrationRun[]>> {
  return apiGet<ConfidenceCalibrationRun[]>("/confidence-calibration/runs", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 1,
    },
  });
}

function listConfidenceCalibrationBins(
  runId: UUID,
  filters: QualityFilters,
): Promise<ApiResult<ConfidenceCalibrationBin[]>> {
  return apiGet<ConfidenceCalibrationBin[]>(`/confidence-calibration/runs/${runId}/bins`, {
    optional: true,
    query: {
      horizon_minutes: filters.horizonMinutes,
      limit: 100,
    },
  });
}

function listWalkForwardValidationRuns(workspaceId: UUID): Promise<ApiResult<WalkForwardValidationRun[]>> {
  return apiGet<WalkForwardValidationRun[]>("/walk-forward-validations/runs", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 1,
    },
  });
}

function listWalkForwardValidationWindows(
  runId: UUID,
  filters: QualityFilters,
): Promise<ApiResult<WalkForwardValidationWindow[]>> {
  return apiGet<WalkForwardValidationWindow[]>(`/walk-forward-validations/runs/${runId}/windows`, {
    optional: true,
    query: {
      horizon_minutes: filters.horizonMinutes,
      limit: 100,
    },
  });
}

function listWalkForwardValidationComparisons(runId: UUID): Promise<ApiResult<WalkForwardValidationComparison[]>> {
  return apiGet<WalkForwardValidationComparison[]>(`/walk-forward-validations/runs/${runId}/comparisons`, {
    optional: true,
  });
}

function listRecentCohortDrift(
  workspaceId: UUID,
  filters: QualityFilters,
): Promise<ApiResult<CohortDriftResult[]>> {
  return apiGet<CohortDriftResult[]>("/cohort-drift/results/recent", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      horizon_minutes: filters.horizonMinutes,
      cohort_key: filters.strategyProfileKey || filters.patternType || filters.timeframe,
      limit: 100,
    },
  });
}

function listPatternAttributionRuns(workspaceId: UUID): Promise<ApiResult<PatternAttributionRun[]>> {
  return apiGet<PatternAttributionRun[]>("/pattern-attribution/runs", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 1,
    },
  });
}

function listPatternAttributionResults(
  runId: UUID,
  filters: QualityFilters,
): Promise<ApiResult<PatternAttributionResult[]>> {
  return apiGet<PatternAttributionResult[]>(`/pattern-attribution/runs/${runId}/results`, {
    optional: true,
    query: {
      pattern_type: filters.patternType,
      limit: 100,
    },
  });
}

function listBacktestExperimentRuns(workspaceId: UUID): Promise<ApiResult<BacktestExperimentRun[]>> {
  return apiGet<BacktestExperimentRun[]>("/backtest-experiments/runs", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 1,
    },
  });
}

function listBacktestExperimentCohorts(runId: UUID): Promise<ApiResult<BacktestExperimentCohort[]>> {
  return apiGet<BacktestExperimentCohort[]>(`/backtest-experiments/runs/${runId}/cohorts`, {
    optional: true,
  });
}

function performanceQuery(workspaceId: UUID, filters: QualityFilters, horizonMinutes: number) {
  return {
    workspace_id: workspaceId,
    horizon_minutes: horizonMinutes,
    symbol_id: filters.symbolId,
    timeframe: filters.timeframe,
    pattern_type: filters.patternType,
    strategy_profile_key: filters.strategyProfileKey,
    start_time: filters.startTime,
    end_time: filters.endTime,
  };
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: QualityFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(qualityFailure(label, result.error));
  return fallback;
}

function readOptionalResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: QualityFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  if (!result.error.missing) {
    failures.push(qualityFailure(label, result.error));
  }
  return fallback;
}

export function qualityApiFailure(result: ApiFailure): QualityFailure {
  return qualityFailure("API request", result.error);
}
