import type {
  AnalysisRun,
  ApiError,
  JournalEntry,
  JsonRecord,
  SignalClassification,
  SignalDigestItem,
  SignalDigestRun,
  SignalOutcome,
  SetupContext,
  SymbolRead,
  UUID,
  Workspace,
} from "@/lib/api/types";

export type OutcomeReviewFilters = {
  workspaceId?: string;
  symbolId?: string;
  timeframe?: string;
  horizonMinutes?: number;
  outcomeLabel?: string;
  onlyMissingJournal: boolean;
};

export type OutcomeReviewFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
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
  average_max_favorable_move: string | null;
  average_max_adverse_move: string | null;
  average_net_move: string | null;
  average_max_favorable_pips: string | null;
  average_max_adverse_pips: string | null;
  average_net_pips: string | null;
  average_max_favorable_ticks: string | null;
  average_max_adverse_ticks: string | null;
  average_net_ticks: string | null;
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
  suggested_change_json: JsonRecord;
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
  bin_config_json: JsonRecord[];
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

export type OutcomeReviewQueueItem = {
  id: UUID;
  signal: SignalClassification;
  analysisRun: AnalysisRun | null;
  symbol: SymbolRead | null;
  outcomes: SignalOutcome[];
  latestOutcome: SignalOutcome;
  journalEntry: JournalEntry | null;
  setupContext: SetupContext | null;
  digestItems: SignalDigestItem[];
  missingContexts: string[];
};

export type OutcomeReviewSummary = {
  queueCount: number;
  reviewedCount: number;
  missingJournalCount: number;
  continuationCount: number;
  reversalCount: number;
  noFollowThroughCount: number;
  insufficientDataCount: number;
};

export type OutcomeReviewData = {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: string | null;
  workspace: Workspace | null;
  workspaces: Workspace[];
  symbols: SymbolRead[];
  filters: OutcomeReviewFilters;
  queue: OutcomeReviewQueueItem[];
  allQueue: OutcomeReviewQueueItem[];
  summary: OutcomeReviewSummary;
  patternPerformance: OutcomePerformanceSummary[];
  profileDiagnostics: StrategyProfileDiagnostic[];
  patternDiagnostics: PatternOutcomeDiagnostic[];
  recommendations: CalibrationRecommendation[];
  calibrationRun: ConfidenceCalibrationRun | null;
  calibrationBins: ConfidenceCalibrationBin[];
  cohortDrift: CohortDriftResult[];
  patternAttributionRun: PatternAttributionRun | null;
  patternAttributionResults: PatternAttributionResult[];
  digests: SignalDigestRun[];
  failures: OutcomeReviewFailure[];
  lastLoadedAt: string;
};

export function outcomeReviewFailure(label: string, error: ApiError): OutcomeReviewFailure {
  return {
    label,
    status: error.status,
    message: error.missing ? "Endpoint not available yet" : error.message,
    missing: error.missing,
  };
}
