export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonRecord = Record<string, JsonValue>;
export type UUID = string;

export type ApiError = {
  status: number;
  code: string;
  message: string;
  url: string;
  missing: boolean;
};

export type ApiSuccess<T> = {
  ok: true;
  status: number;
  url: string;
  data: T;
};

export type ApiFailure = {
  ok: false;
  error: ApiError;
};

export type ApiResult<T> = ApiSuccess<T> | ApiFailure;

export type Workspace = {
  id: UUID;
  name: string;
  created_at: string;
  updated_at: string;
};

export type SymbolRead = {
  id: UUID;
  symbol: string;
  display_name: string;
  market_type: string;
  base_asset: string | null;
  quote_asset: string | null;
  pip_size: string | null;
  tick_size: string | null;
  price_precision: number;
  quantity_precision: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type DataSource = {
  id: UUID;
  workspace_id: UUID;
  name: string;
  source_type: string;
  provider: string;
  status: string;
  credential_ref_id: UUID | null;
  config_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type Watchlist = {
  id: UUID;
  workspace_id: UUID;
  name: string;
  description: string | null;
  status: string;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type WatchlistItem = {
  id: UUID;
  workspace_id: UUID;
  watchlist_id: UUID;
  symbol_id: UUID;
  source_id: UUID | null;
  timeframe: string;
  include_partial_live_candle: boolean;
  is_active: boolean;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type ScheduledScanConfig = {
  id: UUID;
  workspace_id: UUID;
  name: string;
  description: string | null;
  watchlist_id: UUID | null;
  symbol_id: UUID | null;
  source_id: UUID | null;
  timeframe: string | null;
  scan_mode: string;
  lookback_minutes: number;
  interval_seconds: number;
  include_partial_live_candle: boolean;
  include_news_correlation: boolean;
  include_ai_explanation: boolean;
  include_reasoning: boolean;
  include_action_plan: boolean;
  status: string;
  last_run_at: string | null;
  next_run_at: string | null;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type MarketMemorySnapshot = {
  id: UUID;
  workspace_id: UUID;
  symbol_id: UUID;
  source_id: UUID | null;
  timeframe: string;
  state_version: string;
  latest_final_candle_time: string | null;
  latest_analysis_run_id: UUID | null;
  latest_signal_id: UUID | null;
  latest_outcome_id: UUID | null;
  data_quality_label: string;
  freshness_label: string;
  trend_state: string | null;
  volatility_state: string | null;
  range_state: string | null;
  market_regime_label: string | null;
  market_session_label: string | null;
  multi_timeframe_label: string | null;
  cross_asset_label: string | null;
  latest_signal_bias: string | null;
  latest_signal_pattern_type: string | null;
  latest_signal_confidence_label: string | null;
  context_json: JsonRecord;
  warnings_json: JsonRecord[];
  created_at: string;
  updated_at: string;
};

export type AnalysisRun = {
  id: UUID;
  workspace_id: UUID;
  symbol_id: UUID;
  source_id: UUID | null;
  user_id?: UUID | null;
  replayed_from_analysis_run_id?: UUID | null;
  replay_mode?: string | null;
  timeframe: string;
  status: string;
  analysis_mode: string;
  start_time?: string;
  end_time?: string;
  warmup_start_time?: string | null;
  baseline_start_time?: string | null;
  lookback_start?: string | null;
  lookback_end?: string | null;
  candle_count?: number;
  include_partial_live_candle?: boolean;
  include_news_correlation?: boolean;
  include_ai_explanation?: boolean;
  error_code?: string | null;
  error_message?: string | null;
  engine_version?: string;
  rule_set_version?: string;
  engine_snapshot_json?: JsonRecord | null;
  rule_set_snapshot_json?: JsonRecord | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type SignalRead = {
  id: UUID;
  analysis_run_id: UUID;
  workspace_id: UUID;
  symbol_id: UUID;
  timeframe: string;
  strategy_profile_id: UUID | null;
  strategy_profile_key: string | null;
  strategy_profile_version: string | null;
  strategy_profile_snapshot_json: JsonRecord | null;
  bias: string;
  pattern_type: string | null;
  classification_status: string;
  confidence_score: string;
  confidence_label: string;
  candidate_strength: string | null;
  selected_pattern_candidate_id: UUID | null;
  pips_moved: string | null;
  tick_moved: string | null;
  movement_direction: string | null;
  movement_quality: string | null;
  volatility_state: string | null;
  trend_state: string | null;
  range_state: string | null;
  summary: string;
  no_signal_reason: string | null;
  created_at: string;
};

export type SignalConfidenceComponent = {
  id: UUID;
  signal_id: UUID;
  component_name: string;
  component_score: string;
  component_weight: string;
  weighted_score: string;
  reason: string;
  created_at: string;
};

export type SignalEvidence = {
  id: UUID;
  signal_id: UUID;
  evidence_type: string;
  direction: string;
  message: string;
  numeric_value: string | null;
  weight: string;
  metadata_json: JsonRecord;
  created_at: string;
};

export type SignalRiskNote = {
  id: UUID;
  signal_id: UUID;
  code: string;
  message: string;
  severity: string;
  metadata_json: JsonRecord;
  created_at: string;
};

export type SignalClassification = {
  analysis_run_id: UUID;
  signal: SignalRead;
  confidence_components: SignalConfidenceComponent[];
  evidence: SignalEvidence[];
  risk_notes: SignalRiskNote[];
  deterministic_explanation: JsonRecord | null;
  news_correlations: JsonRecord[];
  llm_explanation: JsonRecord | null;
};

export type SignalPriorityScore = {
  id: UUID;
  workspace_id: UUID;
  signal_id: UUID;
  analysis_run_id: UUID;
  symbol_id: UUID;
  timeframe: string;
  priority_version: string;
  priority_score: string;
  priority_label: string;
  review_bucket: string;
  component_scores_json: JsonRecord;
  penalties_json: JsonRecord[];
  boosters_json: JsonRecord[];
  reasons_json: JsonRecord[];
  warnings_json: JsonRecord[];
  created_at: string;
  updated_at: string;
};

export type DashboardSymbolReadModel = {
  id: UUID;
  workspace_id: UUID;
  symbol_id: UUID;
  source_id: UUID | null;
  timeframe: string;
  read_model_version: string;
  latest_final_candle_time: string | null;
  freshness_label: string | null;
  data_quality_label: string | null;
  latest_signal_id: UUID | null;
  latest_bias: string | null;
  latest_pattern_type: string | null;
  latest_confidence_label: string | null;
  latest_priority_score: string | null;
  latest_priority_label: string | null;
  setup_quality_label: string | null;
  market_regime_label: string | null;
  market_session_label: string | null;
  pending_action_count: number;
  warning_count: number;
  summary_json: JsonRecord;
  updated_at: string;
  created_at: string;
};

export type SignalCardReadModel = {
  id: UUID;
  workspace_id: UUID;
  signal_id: UUID;
  analysis_run_id: UUID;
  symbol_id: UUID;
  timeframe: string;
  read_model_version: string;
  classification_status: string;
  bias: string;
  pattern_type: string | null;
  confidence_score: string | null;
  confidence_label: string | null;
  priority_score: string | null;
  priority_label: string | null;
  review_bucket: string | null;
  setup_quality_label: string | null;
  freshness_label: string | null;
  data_quality_label: string | null;
  readiness_label: string | null;
  outcome_summary_json: JsonRecord;
  evidence_summary_json: JsonRecord;
  risk_summary_json: JsonRecord;
  action_summary_json: JsonRecord;
  warning_summary_json: JsonRecord;
  searchable_text: string;
  updated_at: string;
  created_at: string;
};

export type CommandCenterReadModel = {
  id: UUID;
  workspace_id: UUID;
  read_model_version: string;
  period_start: string | null;
  period_end: string | null;
  status: string;
  summary_json: JsonRecord;
  sections_json: JsonRecord;
  warning_count: number;
  generated_at: string;
  created_at: string;
  updated_at: string;
};

export type SignalOutcome = {
  id: UUID;
  workspace_id: UUID;
  analysis_run_id: UUID;
  signal_id: UUID;
  symbol_id: UUID;
  timeframe: string;
  pattern_type: string | null;
  bias: string;
  classification_status: string;
  horizon_minutes: number;
  evaluation_status: string;
  reference_time: string;
  future_window_start: string;
  future_window_end: string;
  future_candle_count: number;
  direction_followed: boolean | null;
  reversal_detected: boolean;
  outcome_label: string;
  movement_quality: string | null;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type DecisionReadinessAssessmentResponse = {
  assessment: {
    readiness_score: number;
    readiness_label: string;
    summary: string;
  };
  blockers: JsonRecord[];
  warnings: JsonRecord[];
  next_steps: string[];
};

export type SetupContext = {
  id: UUID;
  workspace_id: UUID;
  signal_id: UUID;
  analysis_run_id: UUID;
  symbol_id: UUID;
  timeframe: string;
  context_version: string;
  status: string;
  directional_bias: string;
  setup_quality_label: string;
  setup_quality_score: string;
  invalidation_context_json: JsonRecord[];
  observation_zones_json: JsonRecord[];
  target_context_zones_json: JsonRecord[];
  wait_conditions_json: JsonRecord[];
  avoid_reasons_json: JsonRecord[];
  timeframe_agreement_json: JsonRecord;
  data_quality_warnings_json: JsonRecord[];
  risk_notes_json: JsonRecord[];
  next_observations_json: JsonRecord[];
  summary: string;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type AdvancedFeatureSnapshot = {
  id: UUID;
  workspace_id: UUID;
  analysis_run_id: UUID;
  symbol_id: UUID;
  timeframe: string;
  feature_pack_version: string;
  impulse_json: JsonRecord;
  correction_json: JsonRecord;
  wick_pressure_json: JsonRecord;
  movement_efficiency_json: JsonRecord;
  compression_expansion_json: JsonRecord;
  swing_structure_json: JsonRecord;
  support_resistance_json: JsonRecord;
  exhaustion_json: JsonRecord;
  liquidity_sweep_json: JsonRecord;
  warnings_json: JsonRecord;
  summary: string;
  created_at: string;
  updated_at: string;
};

export type SignalDigestRun = {
  id: UUID;
  workspace_id: UUID;
  digest_type: string;
  status: string;
  digest_version: string;
  title: string;
  period_start: string;
  period_end: string;
  timezone: string;
  filters_json: JsonRecord;
  summary_json: JsonRecord;
  section_counts_json: Record<string, number>;
  warnings_json: JsonRecord[];
  created_at: string;
  updated_at: string;
};

export type SignalDigestItem = {
  id: UUID;
  workspace_id: UUID;
  digest_run_id: UUID;
  item_type: string;
  symbol_id: UUID | null;
  signal_id: UUID | null;
  setup_context_id: UUID | null;
  analysis_run_id: UUID | null;
  outcome_id: UUID | null;
  action_item_id: UUID | null;
  news_event_id: UUID | null;
  priority: string;
  title: string;
  summary: string;
  tags_json: string[];
  metadata_json: JsonRecord;
  sort_order: number;
  created_at: string;
};

export type DailyBriefRun = {
  id: UUID;
  workspace_id: UUID;
  digest_id: UUID | null;
  watchlist_id: UUID | null;
  status: string;
  brief_type: string;
  brief_version: string;
  period_start: string;
  period_end: string;
  timezone: string;
  filters_json: JsonRecord;
  summary_json: JsonRecord;
  sections_json: JsonRecord;
  warnings_json: JsonRecord[];
  generated_at: string;
  created_at: string;
  updated_at: string;
};

export type DailyBriefItem = {
  id: UUID;
  workspace_id: UUID;
  brief_run_id: UUID;
  item_type: string;
  priority: string;
  symbol_id: UUID | null;
  signal_id: UUID | null;
  analysis_run_id: UUID | null;
  outcome_id: UUID | null;
  action_item_id: UUID | null;
  setup_context_id: UUID | null;
  source_type: string | null;
  source_id: UUID | null;
  title: string;
  summary: string;
  reason: string;
  tags_json: string[];
  metadata_json: JsonRecord;
  sort_order: number;
  created_at: string;
};

export type JournalEntry = {
  id: UUID;
  workspace_id: UUID;
  user_id: UUID | null;
  signal_id: UUID | null;
  analysis_run_id: UUID | null;
  setup_context_id: UUID | null;
  chart_screenshot_run_id: UUID | null;
  title: string;
  status: string;
  decision_type: string;
  confidence_before: string | null;
  user_bias: string | null;
  user_notes: string;
  tags: string[];
  metadata: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type JournalEntryCreateRequest = {
  workspaceId: UUID;
  userId?: UUID | null;
  signalId?: UUID | null;
  analysisRunId?: UUID | null;
  setupContextId?: UUID | null;
  chartScreenshotRunId?: UUID | null;
  title: string;
  status?: string;
  decisionType: string;
  confidenceBefore?: string | number | null;
  userBias?: string | null;
  userNotes: string;
  tags?: string[];
  metadata?: JsonRecord;
};

export type ActionItem = {
  id: UUID;
  workspace_id: UUID;
  action_plan_id: UUID;
  source_type?: string;
  source_id?: UUID;
  signal_id?: UUID | null;
  analysis_run_id?: UUID | null;
  reasoning_run_id?: UUID | null;
  action_type: string;
  status: string;
  priority?: string;
  source_scenario_id?: UUID | null;
  title?: string;
  description?: string;
  due_at: string | null;
  horizon_minutes?: number | null;
  idempotency_key?: string;
  input_json?: JsonRecord;
  result_json?: JsonRecord | null;
  error_code?: string | null;
  error_message?: string | null;
  attempts?: number;
  max_attempts?: number;
  last_attempted_at?: string | null;
  locked_by?: string | null;
  locked_until?: string | null;
  completed_at?: string | null;
  metadata_json?: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type ActionPlanRead = {
  id: UUID;
  workspace_id: UUID;
  source_type: string;
  source_id: UUID;
  signal_id: UUID | null;
  analysis_run_id: UUID | null;
  reasoning_run_id: UUID | null;
  status: string;
  plan_version: string;
  created_from: string;
  summary: string;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type ActionPlanResponse = {
  plan: ActionPlanRead;
  items: ActionItem[];
  rejected_actions: JsonRecord[];
  skipped_actions: JsonRecord[];
};

export type IntelligenceQualityRun = {
  id: UUID;
  workspace_id: UUID;
  analysis_run_id: UUID | null;
  signal_id: UUID | null;
  source_type: string;
  status: string;
  quality_score: string;
  quality_label: string;
  gate_version: string;
  shadow_version: string;
  checked_at: string;
  summary: string;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type IntelligenceQualityFinding = {
  id: UUID;
  workspace_id: UUID;
  quality_run_id: UUID;
  finding_type: string;
  severity: string;
  code: string;
  title: string;
  message: string;
  artifact_type: string;
  artifact_id: UUID | null;
  expected_value: string | null;
  observed_value: string | null;
  metadata_json: JsonRecord;
  created_at: string;
};

export type ShadowClassificationResult = {
  id: UUID;
  workspace_id: UUID;
  quality_run_id: UUID;
  analysis_run_id: UUID;
  signal_id: UUID | null;
  strategy_profile_key: string;
  strategy_profile_version: string;
  classification_status: string;
  bias: string;
  pattern_type: string | null;
  confidence_score: string | null;
  confidence_label: string | null;
  selected_candidate_id: UUID | null;
  agreement_with_final: string;
  disagreement_reason: string | null;
  metadata_json: JsonRecord;
  created_at: string;
};

export type IntelligenceQualityResponse = {
  quality_run: IntelligenceQualityRun;
  findings: IntelligenceQualityFinding[];
  shadow_classifications: ShadowClassificationResult[];
};

export type HistoricalCaseSignalSummary = {
  signal_id: UUID;
  symbol_id: UUID;
  timeframe: string;
  strategy_profile_key: string | null;
  strategy_profile_version: string | null;
  pattern_type: string | null;
  bias: string;
  classification_status: string;
  confidence_score: string | null;
  confidence_label: string | null;
  summary: string | null;
};

export type HistoricalCaseSearchResult = {
  matched_signal_id: UUID;
  analysis_run_id: UUID;
  similarity_score: string;
  matched_reasons: string[];
  differing_reasons: string[];
  signal_summary: HistoricalCaseSignalSummary;
  outcome_summary: JsonRecord | null;
  deterministic_explanation_summary: string | null;
};

export type HistoricalCaseSearchRead = {
  source_signal_id: UUID | null;
  source_analysis_run_id: UUID | null;
  search_version: string;
  result_count: number;
  results: HistoricalCaseSearchResult[];
};

export type ReasoningRun = {
  id: UUID;
  workspace_id: UUID;
  analysis_run_id: UUID | null;
  signal_id: UUID | null;
  outcome_id: UUID | null;
  source_type: string;
  provider: string;
  model: string;
  prompt_version: string;
  reasoning_type: string;
  status: string;
  input_snapshot_json: JsonRecord;
  output_json: JsonRecord | null;
  output_text: string | null;
  safety_status: string;
  grounding_status: string;
  blocked_terms_json: string[];
  grounding_issues_json: string[];
  tokens_input: number | null;
  tokens_output: number | null;
  estimated_cost: string | null;
  latency_ms: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type ScenarioItem = {
  scenario_type: string;
  scenario_label: string;
  possibility_label: string;
  supporting_evidence: string[];
  conflicting_evidence: string[];
  outcome_history: JsonRecord | null;
  next_observations: string[];
  suggested_backend_actions: string[];
  risk_notes: string[];
};

export type ScenarioReasoningResponse = {
  reasoning_run: ReasoningRun;
  summary: string;
  scenarios: ScenarioItem[];
  limitations: string[];
};

export type MultiTimeframeContext = {
  id: UUID;
  workspace_id: UUID;
  analysis_run_id: UUID | null;
  signal_id: UUID | null;
  symbol_id: UUID;
  source_id: UUID | null;
  primary_timeframe: string;
  context_timeframes_json: string[];
  context_version: string;
  trend_alignment: string;
  volatility_alignment: string;
  range_alignment: string;
  agreement_score: string;
  agreement_label: string;
  context_summary: string;
  context_json: JsonRecord;
  warnings_json: JsonRecord[];
  created_at: string;
  updated_at: string;
};

export type CrossAssetContextRun = {
  id: UUID;
  workspace_id: UUID;
  analysis_run_id: UUID | null;
  signal_id: UUID | null;
  base_symbol_id: UUID;
  timeframe: string;
  source_id: UUID | null;
  context_version: string;
  status: string;
  start_time: string;
  end_time: string;
  compared_symbol_count: number;
  result_count: number;
  summary: string;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type CrossAssetContextResult = {
  id: UUID;
  workspace_id: UUID;
  context_run_id: UUID;
  base_symbol_id: UUID;
  compared_symbol_id: UUID;
  timeframe: string;
  start_time: string;
  end_time: string;
  base_move: string;
  compared_move: string;
  base_direction: string;
  compared_direction: string;
  correlation_score: string;
  alignment_label: string;
  lead_lag_offset_candles: number | null;
  lead_lag_label: string;
  divergence_score: string;
  data_quality_label: string;
  metadata_json: JsonRecord;
  created_at: string;
};

export type HealthResponse = {
  status: string;
  service: string;
  environment: string;
};

export type WorkerStatusResponse = {
  status: string;
  database: string;
  live_feed_worker: JsonRecord;
  stale_monitor: JsonRecord;
  redis: JsonRecord;
};

export type IntelligenceReport = {
  report_type: string;
  generated_at: string;
  workspace_id: UUID;
  subject: {
    type: string;
    id: UUID;
  };
  sections: JsonRecord;
  warnings: string[];
  missing_sections: string[];
};

export type AuditTimeline = {
  subject: JsonRecord;
  generated_at: string;
  completeness_score: number;
  events: JsonRecord[];
  artifact_graph: JsonRecord | null;
  warnings: string[];
  missing_sections: string[];
};

export type ContextRead = JsonRecord & {
  id?: UUID;
  signal_id?: UUID;
  analysis_run_id?: UUID;
  label?: string;
  regime_label?: string;
  session_label?: string;
  created_at?: string;
};
