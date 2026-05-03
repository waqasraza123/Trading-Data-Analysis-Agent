import type { ApiError, JsonRecord, SymbolRead, UUID, Workspace } from "@/lib/api/types";

export type QualityFilters = {
  workspaceId?: string;
  strategyProfileKey?: string;
  symbolId?: string;
  timeframe?: string;
  patternType?: string;
  horizonMinutes?: number;
  startTime?: string;
  endTime?: string;
};

export type QualityFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type StrategyProfileRead = {
  id: UUID;
  key: string;
  version: string;
  name: string;
  description: string | null;
  is_active: boolean;
  allowed_patterns_json: string[];
  excluded_patterns_json: string[];
  created_at: string;
  updated_at: string;
};

export type OutcomePerformanceSummary = {
  group_key: string;
  pattern_type: string | null;
  strategy_profile_key: string | null;
  symbol_id: UUID | null;
  timeframe: string | null;
  horizon_minutes: number;
  evaluated_count: number;
  continuation_count: number;
  partial_follow_through_count: number;
  reversal_count: number;
  no_follow_through_count: number;
  insufficient_data_count: number;
  continuation_rate: string;
  reversal_rate: string;
  historical_follow_through_rate: string;
};

export type StrategyProfileDiagnostic = {
  id: UUID;
  workspace_id: UUID;
  diagnostic_run_id: UUID;
  strategy_profile_key: string;
  strategy_profile_version: string | null;
  symbol_id: UUID | null;
  timeframe: string | null;
  horizon_minutes: number;
  sample_size: number;
  evaluated_count: number;
  continuation_count: number;
  partial_follow_through_count: number;
  no_follow_through_count: number;
  reversal_count: number;
  insufficient_data_count: number;
  continuation_rate: string;
  reversal_rate: string;
  no_follow_through_rate: string;
  average_confidence_score: string | null;
  confidence_alignment_score: string | null;
  diagnostic_label: string;
  diagnostic_summary: string;
  metadata_json: JsonRecord;
  created_at: string;
};

export type PatternOutcomeDiagnostic = {
  id: UUID;
  workspace_id: UUID;
  diagnostic_run_id: UUID;
  pattern_type: string;
  strategy_profile_key: string | null;
  symbol_id: UUID | null;
  timeframe: string | null;
  horizon_minutes: number;
  sample_size: number;
  evaluated_count: number;
  continuation_rate: string;
  reversal_rate: string;
  no_follow_through_rate: string;
  average_confidence_score: string | null;
  confidence_alignment_score: string | null;
  diagnostic_label: string;
  diagnostic_summary: string;
  metadata_json: JsonRecord;
  created_at: string;
};

export type CalibrationRecommendation = {
  id: UUID;
  workspace_id: UUID;
  diagnostic_run_id: UUID;
  recommendation_type: string;
  strategy_profile_key: string | null;
  strategy_profile_version: string | null;
  pattern_type: string | null;
  symbol_id: UUID | null;
  timeframe: string | null;
  horizon_minutes: number | null;
  severity: string;
  status: string;
  title: string;
  rationale: string;
  evidence_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type ConfidenceCalibrationRun = {
  id: UUID;
  workspace_id: UUID;
  status: string;
  calibration_version: string;
  filters_json: JsonRecord;
  horizons_json: number[];
  minimum_sample_size: number;
  evaluated_signal_count: number;
  evaluated_outcome_count: number;
  bin_count: number;
  summary: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type ConfidenceCalibrationBin = {
  id: UUID;
  workspace_id: UUID;
  calibration_run_id: UUID;
  horizon_minutes: number;
  bin_label: string;
  sample_size: number;
  evaluated_count: number;
  continuation_count: number;
  partial_follow_through_count: number;
  no_follow_through_count: number;
  reversal_count: number;
  insufficient_data_count: number;
  continuation_rate: string;
  reversal_rate: string;
  no_follow_through_rate: string;
  average_confidence_score: string;
  confidence_alignment_score: string;
  calibration_label: string;
  metadata_json: JsonRecord;
  created_at: string;
};

export type WalkForwardValidationRun = {
  id: UUID;
  workspace_id: UUID;
  name: string;
  status: string;
  validation_version: string;
  filters_json: JsonRecord;
  window_config_json: JsonRecord;
  horizons_json: number[];
  minimum_sample_size: number;
  window_count: number;
  evaluated_signal_count: number;
  evaluated_outcome_count: number;
  summary: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type WalkForwardValidationWindow = {
  id: UUID;
  workspace_id: UUID;
  validation_run_id: UUID;
  window_index: number;
  window_start: string;
  window_end: string;
  horizon_minutes: number;
  sample_size: number;
  evaluated_count: number;
  continuation_count: number;
  partial_follow_through_count: number;
  no_follow_through_count: number;
  reversal_count: number;
  insufficient_data_count: number;
  continuation_rate: string;
  reversal_rate: string;
  no_follow_through_rate: string;
  average_confidence_score: string | null;
  confidence_alignment_score: string | null;
  stability_label: string;
  summary: string;
  metadata_json: JsonRecord;
  created_at: string;
};

export type WalkForwardValidationComparison = {
  id: UUID;
  workspace_id: UUID;
  validation_run_id: UUID;
  horizon_minutes: number;
  compared_window_count: number;
  stability_score: string;
  degradation_detected: boolean;
  improvement_detected: boolean;
  summary: string;
  metadata_json: JsonRecord;
  created_at: string;
};

export type CohortDriftResult = {
  id: UUID;
  workspace_id: UUID;
  drift_run_id: UUID;
  cohort_key: string;
  cohort_dimensions_json: JsonRecord;
  horizon_minutes: number;
  baseline_sample_size: number;
  comparison_sample_size: number;
  baseline_continuation_rate: string | null;
  comparison_continuation_rate: string | null;
  continuation_rate_delta: string | null;
  baseline_reversal_rate: string | null;
  comparison_reversal_rate: string | null;
  reversal_rate_delta: string | null;
  baseline_no_follow_through_rate: string | null;
  comparison_no_follow_through_rate: string | null;
  no_follow_through_delta: string | null;
  baseline_confidence_alignment: string | null;
  comparison_confidence_alignment: string | null;
  confidence_alignment_delta: string | null;
  drift_score: string;
  drift_label: string;
  severity: string;
  summary: string;
  metadata_json: JsonRecord;
  created_at: string;
};

export type PatternAttributionRun = {
  id: UUID;
  workspace_id: UUID;
  status: string;
  attribution_version: string;
  filters_json: JsonRecord;
  horizons_json: number[];
  minimum_sample_size: number;
  evaluated_candidate_count: number;
  evaluated_signal_count: number;
  result_count: number;
  summary: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type PatternAttributionResult = {
  id: UUID;
  workspace_id: UUID;
  attribution_run_id: UUID;
  pattern_type: string;
  strategy_profile_key: string | null;
  symbol_id: UUID | null;
  timeframe: string | null;
  horizon_minutes: number | null;
  candidate_count: number;
  selected_count: number;
  rejected_count: number;
  blocked_count: number;
  average_strength_score: string | null;
  average_selected_confidence: string | null;
  continuation_count: number;
  partial_follow_through_count: number;
  no_follow_through_count: number;
  reversal_count: number;
  insufficient_data_count: number;
  continuation_rate: string | null;
  reversal_rate: string | null;
  no_follow_through_rate: string | null;
  attribution_label: string;
  diagnostic_summary: string;
  metadata_json: JsonRecord;
  created_at: string;
};

export type BacktestExperimentRun = {
  id: UUID;
  workspace_id: UUID;
  name: string;
  description: string | null;
  status: string;
  experiment_version: string;
  filters_json: JsonRecord;
  cohort_dimensions_json: string[];
  horizons_json: number[];
  minimum_sample_size: number;
  signal_count: number;
  outcome_count: number;
  cohort_count: number;
  summary: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type BacktestExperimentCohort = {
  id: UUID;
  workspace_id: UUID;
  experiment_run_id: UUID;
  cohort_key: string;
  cohort_dimensions_json: JsonRecord;
  horizon_minutes: number;
  sample_size: number;
  evaluated_count: number;
  continuation_count: number;
  partial_follow_through_count: number;
  no_follow_through_count: number;
  reversal_count: number;
  insufficient_data_count: number;
  continuation_rate: string;
  reversal_rate: string;
  no_follow_through_rate: string;
  average_confidence_score: string | null;
  cohort_label: string;
  summary: string;
  metadata_json: JsonRecord;
  created_at: string;
};

export type QualitySummary = {
  strongObservedFollowThrough: number;
  profilesNeedingReview: number;
  elevatedReversalPatterns: number;
  degradedSymbolTimeframes: number;
  confidenceCalibrationWarnings: number;
  driftDetected: number;
};

export type ProfileReliabilityRow = {
  key: string;
  sampleSize: number;
  continuationRate: number | null;
  reversalRate: number | null;
  noFollowThroughRate: number | null;
  confidenceAlignment: number | null;
  diagnosticLabel: string;
  recommendationStatus: string | null;
  summary: string;
};

export type PatternAttributionRow = {
  patternType: string;
  selectedCount: number;
  rejectedCount: number;
  blockedCount: number;
  observedOutcomes: string;
  continuationRate: number | null;
  reversalRate: number | null;
  noFollowThroughRate: number | null;
  diagnosticLabel: string;
  summary: string;
};

export type ConfidenceCalibrationRow = {
  id: UUID;
  binLabel: string;
  horizonMinutes: number;
  sampleSize: number;
  alignmentScore: number | null;
  averageConfidence: number | null;
  calibrationLabel: string;
  continuationRate: number | null;
  reversalRate: number | null;
  noFollowThroughRate: number | null;
};

export type WalkForwardRow = {
  id: UUID;
  windowLabel: string;
  horizonMinutes: number;
  sampleSize: number;
  continuationRate: number | null;
  reversalRate: number | null;
  stabilityLabel: string;
  trendLabel: string;
  summary: string;
};

export type CohortDriftRow = {
  id: UUID;
  affectedCohort: string;
  horizonMinutes: number;
  baselineSampleSize: number;
  recentSampleSize: number;
  baselineContinuationRate: number | null;
  recentContinuationRate: number | null;
  baselineReversalRate: number | null;
  recentReversalRate: number | null;
  driftLabel: string;
  severity: string;
  summary: string;
};

export type SymbolTimeframeQualityRow = {
  id: string;
  symbol: string;
  timeframe: string;
  observedFollowThrough: number | null;
  reversalRate: number | null;
  dataQuality: string;
  sampleSize: number;
  diagnosticLabel: string;
};

export type QualityWarning = {
  id: string;
  title: string;
  detail: string;
  severity: "info" | "warning" | "danger";
};

export type QualityFilterOption = {
  value: string;
  label: string;
};

export type QualityScoreboardData = {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: string | null;
  workspace: Workspace | null;
  workspaces: Workspace[];
  symbols: SymbolRead[];
  strategyProfiles: StrategyProfileRead[];
  filters: QualityFilters;
  filterOptions: {
    strategyProfiles: QualityFilterOption[];
    symbols: QualityFilterOption[];
    timeframes: QualityFilterOption[];
    patterns: QualityFilterOption[];
    horizons: QualityFilterOption[];
  };
  summary: QualitySummary;
  profileRows: ProfileReliabilityRow[];
  patternRows: PatternAttributionRow[];
  calibrationRows: ConfidenceCalibrationRow[];
  walkForwardRows: WalkForwardRow[];
  cohortDriftRows: CohortDriftRow[];
  symbolTimeframeRows: SymbolTimeframeQualityRow[];
  warnings: QualityWarning[];
  failures: QualityFailure[];
  endpoints: string[];
  hasAnyQualityData: boolean;
  lastLoadedAt: string;
};

export function qualityFailure(label: string, error: ApiError): QualityFailure {
  return {
    label,
    status: error.status,
    message: error.missing ? "Endpoint not available yet" : error.message,
    missing: error.missing,
  };
}
