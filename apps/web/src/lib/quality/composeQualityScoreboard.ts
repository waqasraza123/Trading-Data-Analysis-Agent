import { humanizeLabel } from "@/lib/formatting/labels";
import type {
  BacktestExperimentCohort,
  CalibrationRecommendation,
  CohortDriftResult,
  CohortDriftRow,
  ConfidenceCalibrationBin,
  ConfidenceCalibrationRow,
  OutcomePerformanceSummary,
  PatternAttributionResult,
  PatternAttributionRow,
  PatternOutcomeDiagnostic,
  ProfileReliabilityRow,
  QualityFilterOption,
  QualityFilters,
  QualityScoreboardData,
  QualitySummary,
  QualityWarning,
  StrategyProfileDiagnostic,
  SymbolTimeframeQualityRow,
  WalkForwardRow,
  WalkForwardValidationComparison,
  WalkForwardValidationWindow,
} from "./types";

type QualityComposeInput = {
  data: Omit<
    QualityScoreboardData,
    | "filterOptions"
    | "summary"
    | "profileRows"
    | "patternRows"
    | "calibrationRows"
    | "walkForwardRows"
    | "cohortDriftRows"
    | "symbolTimeframeRows"
    | "warnings"
    | "hasAnyQualityData"
  >;
  profilePerformance: OutcomePerformanceSummary[];
  patternPerformance: OutcomePerformanceSummary[];
  symbolPerformance: OutcomePerformanceSummary[];
  profileDiagnostics: StrategyProfileDiagnostic[];
  patternDiagnostics: PatternOutcomeDiagnostic[];
  recommendations: CalibrationRecommendation[];
  calibrationBins: ConfidenceCalibrationBin[];
  walkForwardWindows: WalkForwardValidationWindow[];
  walkForwardComparisons: WalkForwardValidationComparison[];
  cohortDrift: CohortDriftResult[];
  patternAttribution: PatternAttributionResult[];
  backtestCohorts: BacktestExperimentCohort[];
};

export function composeQualityScoreboard(input: QualityComposeInput): QualityScoreboardData {
  const profileRows = profileReliabilityRows(input.profileDiagnostics, input.profilePerformance, input.recommendations);
  const patternRows = patternAttributionRows(input.patternAttribution, input.patternDiagnostics, input.patternPerformance);
  const calibrationRows = confidenceCalibrationRows(input.calibrationBins);
  const walkForwardRows = walkForwardValidationRows(input.walkForwardWindows, input.walkForwardComparisons);
  const cohortDriftRows = cohortDriftResultRows(input.cohortDrift);
  const symbolTimeframeRows = symbolTimeframeQualityRows(input.symbolPerformance, input.backtestCohorts, input.data.symbols);
  const summary = summarizeQuality(profileRows, patternRows, calibrationRows, cohortDriftRows, symbolTimeframeRows);
  const warnings = buildWarnings(input.data.failures, summary, profileRows, calibrationRows, cohortDriftRows, symbolTimeframeRows);
  const hasAnyQualityData =
    profileRows.length > 0 ||
    patternRows.length > 0 ||
    calibrationRows.length > 0 ||
    walkForwardRows.length > 0 ||
    cohortDriftRows.length > 0 ||
    symbolTimeframeRows.length > 0;

  return {
    ...input.data,
    filterOptions: buildFilterOptions(input),
    summary,
    profileRows,
    patternRows,
    calibrationRows,
    walkForwardRows,
    cohortDriftRows,
    symbolTimeframeRows,
    warnings,
    hasAnyQualityData,
  };
}

export function parseQualityFilters(params: Record<string, string | undefined>): QualityFilters {
  return {
    workspaceId: params.workspaceId,
    strategyProfileKey: params.strategyProfileKey || params.strategyProfile,
    symbolId: params.symbolId,
    timeframe: params.timeframe,
    patternType: params.patternType || params.pattern,
    horizonMinutes: parsePositiveNumber(params.horizonMinutes || params.horizon),
    startTime: params.startTime || params.startDate,
    endTime: params.endTime || params.endDate,
  };
}

export function matchesQualityFilters(filters: QualityFilters, workspaceId: string): QualityFilters {
  return {
    ...filters,
    workspaceId,
  };
}

function parsePositiveNumber(value: string | undefined): number | undefined {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

function profileReliabilityRows(
  diagnostics: StrategyProfileDiagnostic[],
  performance: OutcomePerformanceSummary[],
  recommendations: CalibrationRecommendation[],
): ProfileReliabilityRow[] {
  const rows = new Map<string, ProfileReliabilityRow>();
  for (const item of diagnostics) {
    rows.set(item.strategy_profile_key, {
      key: item.strategy_profile_key,
      sampleSize: item.sample_size || item.evaluated_count,
      continuationRate: numericRate(item.continuation_rate),
      reversalRate: numericRate(item.reversal_rate),
      noFollowThroughRate: numericRate(item.no_follow_through_rate),
      confidenceAlignment: numericRate(item.confidence_alignment_score),
      diagnosticLabel: item.diagnostic_label,
      recommendationStatus: recommendationStatus(recommendations, item.strategy_profile_key),
      summary: item.diagnostic_summary,
    });
  }
  for (const item of performance) {
    const key = item.strategy_profile_key || item.group_key;
    if (!key || rows.has(key)) {
      continue;
    }
    rows.set(key, {
      key,
      sampleSize: item.evaluated_count,
      continuationRate: numericRate(item.continuation_rate),
      reversalRate: numericRate(item.reversal_rate),
      noFollowThroughRate: noFollowThroughPerformanceRate(item),
      confidenceAlignment: null,
      diagnosticLabel: diagnosticFromPerformance(item),
      recommendationStatus: recommendationStatus(recommendations, key),
      summary: `${item.evaluated_count} evaluated outcomes at ${item.horizon_minutes} minute horizon.`,
    });
  }
  return Array.from(rows.values()).sort((left, right) => right.sampleSize - left.sampleSize);
}

function patternAttributionRows(
  attribution: PatternAttributionResult[],
  diagnostics: PatternOutcomeDiagnostic[],
  performance: OutcomePerformanceSummary[],
): PatternAttributionRow[] {
  const rows = new Map<string, PatternAttributionRow>();
  for (const item of attribution) {
    rows.set(item.pattern_type, {
      patternType: item.pattern_type,
      selectedCount: item.selected_count,
      rejectedCount: item.rejected_count,
      blockedCount: item.blocked_count,
      observedOutcomes: observedOutcomeText(item.continuation_count, item.reversal_count, item.no_follow_through_count),
      continuationRate: numericRate(item.continuation_rate),
      reversalRate: numericRate(item.reversal_rate),
      noFollowThroughRate: numericRate(item.no_follow_through_rate),
      diagnosticLabel: item.attribution_label,
      summary: item.diagnostic_summary,
    });
  }
  for (const item of diagnostics) {
    if (rows.has(item.pattern_type)) {
      continue;
    }
    rows.set(item.pattern_type, {
      patternType: item.pattern_type,
      selectedCount: 0,
      rejectedCount: 0,
      blockedCount: 0,
      observedOutcomes: `${item.evaluated_count} evaluated outcomes`,
      continuationRate: numericRate(item.continuation_rate),
      reversalRate: numericRate(item.reversal_rate),
      noFollowThroughRate: numericRate(item.no_follow_through_rate),
      diagnosticLabel: item.diagnostic_label,
      summary: item.diagnostic_summary,
    });
  }
  for (const item of performance) {
    const patternType = item.pattern_type || item.group_key;
    if (!patternType || rows.has(patternType)) {
      continue;
    }
    rows.set(patternType, {
      patternType,
      selectedCount: 0,
      rejectedCount: 0,
      blockedCount: 0,
      observedOutcomes: observedOutcomeText(item.continuation_count + item.partial_follow_through_count, item.reversal_count, item.no_follow_through_count),
      continuationRate: numericRate(item.continuation_rate),
      reversalRate: numericRate(item.reversal_rate),
      noFollowThroughRate: noFollowThroughPerformanceRate(item),
      diagnosticLabel: diagnosticFromPerformance(item),
      summary: `${item.evaluated_count} evaluated outcomes at ${item.horizon_minutes} minute horizon.`,
    });
  }
  return Array.from(rows.values()).sort((left, right) => (right.reversalRate || 0) - (left.reversalRate || 0));
}

function confidenceCalibrationRows(bins: ConfidenceCalibrationBin[]): ConfidenceCalibrationRow[] {
  return bins.map((item) => ({
    id: item.id,
    binLabel: item.bin_label,
    horizonMinutes: item.horizon_minutes,
    sampleSize: item.sample_size || item.evaluated_count,
    alignmentScore: numericRate(item.confidence_alignment_score),
    averageConfidence: numericRate(item.average_confidence_score),
    calibrationLabel: item.calibration_label,
    continuationRate: numericRate(item.continuation_rate),
    reversalRate: numericRate(item.reversal_rate),
    noFollowThroughRate: numericRate(item.no_follow_through_rate),
  }));
}

function walkForwardValidationRows(
  windows: WalkForwardValidationWindow[],
  comparisons: WalkForwardValidationComparison[],
): WalkForwardRow[] {
  const comparisonByHorizon = new Map(comparisons.map((item) => [item.horizon_minutes, item]));
  return windows.map((item) => {
    const comparison = comparisonByHorizon.get(item.horizon_minutes) || null;
    return {
      id: item.id,
      windowLabel: `${dateLabel(item.window_start)} to ${dateLabel(item.window_end)}`,
      horizonMinutes: item.horizon_minutes,
      sampleSize: item.sample_size || item.evaluated_count,
      continuationRate: numericRate(item.continuation_rate),
      reversalRate: numericRate(item.reversal_rate),
      stabilityLabel: item.stability_label,
      trendLabel: trendLabel(comparison),
      summary: item.summary || comparison?.summary || "Window evaluated against stored deterministic outcomes.",
    };
  });
}

function cohortDriftResultRows(results: CohortDriftResult[]): CohortDriftRow[] {
  return results.map((item) => ({
    id: item.id,
    affectedCohort: readableCohort(item.cohort_key, item.cohort_dimensions_json),
    horizonMinutes: item.horizon_minutes,
    baselineSampleSize: item.baseline_sample_size,
    recentSampleSize: item.comparison_sample_size,
    baselineContinuationRate: numericRate(item.baseline_continuation_rate),
    recentContinuationRate: numericRate(item.comparison_continuation_rate),
    baselineReversalRate: numericRate(item.baseline_reversal_rate),
    recentReversalRate: numericRate(item.comparison_reversal_rate),
    driftLabel: item.drift_label,
    severity: item.severity,
    summary: item.summary,
  }));
}

function symbolTimeframeQualityRows(
  symbolPerformance: OutcomePerformanceSummary[],
  backtestCohorts: BacktestExperimentCohort[],
  symbols: QualityComposeInput["data"]["symbols"],
): SymbolTimeframeQualityRow[] {
  const symbolMap = new Map(symbols.map((symbol) => [symbol.id, symbol]));
  const rows = new Map<string, SymbolTimeframeQualityRow>();
  for (const item of symbolPerformance) {
    const id = `${item.symbol_id || item.group_key}:${item.timeframe || "all"}`;
    rows.set(id, {
      id,
      symbol: symbolLabel(item.symbol_id, item.group_key, symbolMap),
      timeframe: item.timeframe || "All",
      observedFollowThrough: numericRate(item.continuation_rate),
      reversalRate: numericRate(item.reversal_rate),
      dataQuality: item.insufficient_data_count > 0 ? "Review data coverage" : "Evaluated",
      sampleSize: item.evaluated_count,
      diagnosticLabel: diagnosticFromPerformance(item),
    });
  }
  for (const item of backtestCohorts) {
    const symbolId = stringDimension(item.cohort_dimensions_json.symbol_id);
    const timeframe = stringDimension(item.cohort_dimensions_json.timeframe) || "All";
    if (!symbolId && timeframe === "All") {
      continue;
    }
    const id = `${symbolId || item.cohort_key}:${timeframe}`;
    if (rows.has(id)) {
      continue;
    }
    rows.set(id, {
      id,
      symbol: symbolLabel(symbolId, item.cohort_key, symbolMap),
      timeframe,
      observedFollowThrough: numericRate(item.continuation_rate),
      reversalRate: numericRate(item.reversal_rate),
      dataQuality: item.insufficient_data_count > 0 ? "Review data coverage" : "Evaluated",
      sampleSize: item.sample_size || item.evaluated_count,
      diagnosticLabel: item.cohort_label,
    });
  }
  return Array.from(rows.values()).sort((left, right) => (right.reversalRate || 0) - (left.reversalRate || 0));
}

function summarizeQuality(
  profileRows: ProfileReliabilityRow[],
  patternRows: PatternAttributionRow[],
  calibrationRows: ConfidenceCalibrationRow[],
  cohortDriftRows: CohortDriftRow[],
  symbolRows: SymbolTimeframeQualityRow[],
): QualitySummary {
  return {
    strongObservedFollowThrough: profileRows.filter((item) => (item.continuationRate || 0) >= 0.65 && item.sampleSize >= 10).length,
    profilesNeedingReview: profileRows.filter((item) => needsReview(item.diagnosticLabel) || item.recommendationStatus).length,
    elevatedReversalPatterns: patternRows.filter((item) => (item.reversalRate || 0) >= 0.3 || needsReview(item.diagnosticLabel)).length,
    degradedSymbolTimeframes: symbolRows.filter((item) => needsReview(item.diagnosticLabel) || item.dataQuality !== "Evaluated").length,
    confidenceCalibrationWarnings: calibrationRows.filter((item) => calibrationWarning(item.calibrationLabel)).length,
    driftDetected: cohortDriftRows.filter((item) => item.severity !== "none" && item.driftLabel !== "stable").length,
  };
}

function buildWarnings(
  failures: QualityComposeInput["data"]["failures"],
  summary: QualitySummary,
  profileRows: ProfileReliabilityRow[],
  calibrationRows: ConfidenceCalibrationRow[],
  cohortDriftRows: CohortDriftRow[],
  symbolRows: SymbolTimeframeQualityRow[],
): QualityWarning[] {
  const warnings: QualityWarning[] = [];
  if (failures.some((failure) => !failure.missing)) {
    warnings.push({
      id: "api-failures",
      title: "Some quality inputs are unavailable",
      detail: "The scoreboard is rendering the available read-only diagnostic data.",
      severity: "warning",
    });
  }
  if (summary.profilesNeedingReview > 0) {
    warnings.push({
      id: "profiles-review",
      title: "Profile review recommended",
      detail: `${summary.profilesNeedingReview} profile rows show diagnostic labels or recommendations that need operator review.`,
      severity: "warning",
    });
  }
  if (summary.confidenceCalibrationWarnings > 0) {
    warnings.push({
      id: "calibration-warning",
      title: "Confidence alignment warning",
      detail: `${summary.confidenceCalibrationWarnings} confidence bins are labeled overconfidence or underconfidence.`,
      severity: "warning",
    });
  }
  if (summary.driftDetected > 0) {
    warnings.push({
      id: "cohort-drift",
      title: "Cohort drift detected",
      detail: `${summary.driftDetected} recent cohorts differ from their baseline behavior.`,
      severity: cohortDriftRows.some((item) => item.severity === "severe") ? "danger" : "warning",
    });
  }
  if (symbolRows.some((item) => item.dataQuality !== "Evaluated")) {
    warnings.push({
      id: "data-coverage",
      title: "Data coverage review",
      detail: "Some symbol/timeframe cohorts include insufficient outcome data.",
      severity: "info",
    });
  }
  if (profileRows.length === 0 && calibrationRows.length === 0) {
    warnings.push({
      id: "run-diagnostics-first",
      title: "Run diagnostics first",
      detail: "No profile diagnostics or confidence calibration bins were returned for this workspace.",
      severity: "info",
    });
  }
  return warnings;
}

function buildFilterOptions(input: QualityComposeInput): QualityScoreboardData["filterOptions"] {
  const timeframes = uniqueOptions([
    ...input.symbolPerformance.map((item) => item.timeframe),
    ...input.profileDiagnostics.map((item) => item.timeframe),
    ...input.patternDiagnostics.map((item) => item.timeframe),
  ]);
  const patterns = uniqueOptions([
    ...input.patternPerformance.map((item) => item.pattern_type),
    ...input.patternDiagnostics.map((item) => item.pattern_type),
    ...input.patternAttribution.map((item) => item.pattern_type),
  ]);
  const horizons = uniqueOptions([
    ...input.profilePerformance.map((item) => String(item.horizon_minutes)),
    ...input.patternPerformance.map((item) => String(item.horizon_minutes)),
    ...input.symbolPerformance.map((item) => String(item.horizon_minutes)),
    ...input.calibrationBins.map((item) => String(item.horizon_minutes)),
    ...input.walkForwardWindows.map((item) => String(item.horizon_minutes)),
    ...input.cohortDrift.map((item) => String(item.horizon_minutes)),
  ]);
  return {
    strategyProfiles: input.data.strategyProfiles.map((item) => ({ value: item.key, label: item.name || humanizeLabel(item.key) })),
    symbols: input.data.symbols.map((item) => ({ value: item.id, label: item.display_name || item.symbol })),
    timeframes,
    patterns,
    horizons: horizons.sort((left, right) => Number(left.value) - Number(right.value)),
  };
}

function uniqueOptions(values: Array<string | null | undefined>): QualityFilterOption[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort().map((value) => ({
    value,
    label: humanizeLabel(value),
  }));
}

function numericRate(value: string | number | null | undefined): number | null {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function noFollowThroughPerformanceRate(item: OutcomePerformanceSummary): number | null {
  if (item.evaluated_count <= 0) {
    return null;
  }
  return (item.no_follow_through_count + item.insufficient_data_count) / item.evaluated_count;
}

function diagnosticFromPerformance(item: OutcomePerformanceSummary): string {
  const reversalRate = numericRate(item.reversal_rate) || 0;
  const continuationRate = numericRate(item.continuation_rate) || 0;
  const noFollowThroughRate = noFollowThroughPerformanceRate(item) || 0;
  if (reversalRate >= 0.3) {
    return "elevated_reversal";
  }
  if (noFollowThroughRate >= 0.35) {
    return "review_recommended";
  }
  if (continuationRate >= 0.65) {
    return "strong_observed_follow_through";
  }
  return "observed_behavior";
}

function recommendationStatus(recommendations: CalibrationRecommendation[], strategyProfileKey: string): string | null {
  return recommendations.find((item) => item.strategy_profile_key === strategyProfileKey)?.status || null;
}

function observedOutcomeText(continuation: number, reversal: number, noFollowThrough: number): string {
  return `${continuation} continuation · ${reversal} reversal · ${noFollowThrough} no follow-through`;
}

function trendLabel(comparison: WalkForwardValidationComparison | null): string {
  if (!comparison) {
    return "Window only";
  }
  if (comparison.degradation_detected && comparison.improvement_detected) {
    return "Mixed";
  }
  if (comparison.degradation_detected) {
    return "Degrading";
  }
  if (comparison.improvement_detected) {
    return "Improving";
  }
  return "Stable";
}

function dateLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }
  return date.toISOString().slice(0, 10);
}

function readableCohort(cohortKey: string, dimensions: Record<string, unknown>): string {
  const values = Object.entries(dimensions)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => `${humanizeLabel(key)} ${String(value)}`);
  return values.length > 0 ? values.join(" · ") : humanizeLabel(cohortKey);
}

function symbolLabel(
  symbolId: string | null | undefined,
  fallback: string,
  symbolMap: Map<string, { symbol: string; display_name: string }>,
): string {
  if (symbolId && symbolMap.has(symbolId)) {
    const symbol = symbolMap.get(symbolId);
    return symbol?.display_name || symbol?.symbol || fallback;
  }
  return humanizeLabel(fallback);
}

function stringDimension(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

function needsReview(value: string | null | undefined): boolean {
  const normalized = value?.toLowerCase() || "";
  return normalized.includes("review") || normalized.includes("degraded") || normalized.includes("reversal") || normalized.includes("drift");
}

function calibrationWarning(value: string | null | undefined): boolean {
  const normalized = value?.toLowerCase() || "";
  return normalized.includes("over") || normalized.includes("under") || normalized.includes("degraded");
}
