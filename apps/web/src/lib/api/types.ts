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
  timeframe: string;
  status: string;
  analysis_mode: string;
  lookback_start: string | null;
  lookback_end: string | null;
  candle_count: number;
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

export type ActionItem = {
  id: UUID;
  workspace_id: UUID;
  action_plan_id: UUID;
  action_type: string;
  status: string;
  source_scenario_id: UUID | null;
  title: string;
  description: string;
  due_at: string | null;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
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
