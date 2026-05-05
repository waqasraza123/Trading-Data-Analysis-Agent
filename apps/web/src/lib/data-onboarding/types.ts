import type {
  ApiError,
  JsonRecord,
  MarketMemorySnapshot,
  SymbolRead,
  UUID,
  Workspace,
} from "@/lib/api/types";
import type {
  ProviderHealthSnapshot,
  ProviderHealthSummary,
} from "@/lib/provider-health/types";

export const onboardingTimeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"] as const;

export type OnboardingTimeframe = (typeof onboardingTimeframes)[number];

export type OnboardingStepKey =
  | "data_source"
  | "credentials"
  | "symbols_timeframes"
  | "freshness"
  | "gaps"
  | "recovery"
  | "summary";

export type DataHealthStatus =
  | "ready"
  | "degraded"
  | "missing_data"
  | "stale"
  | "recovery_needed"
  | "backend_unavailable";

export type OnboardingFailure = {
  label: string;
  message: string;
  status: number;
  missing: boolean;
};

export type OnboardingInitialData = {
  appName: string;
  apiBaseUrl: string;
  workspace: Workspace | null;
  workspaces: Workspace[];
  symbols: SymbolRead[];
  dataSources: DataSource[];
  memorySnapshots: MarketMemorySnapshot[];
  providerHealthSnapshots: ProviderHealthSnapshot[];
  providerHealthSummary: ProviderHealthSummary | null;
  providerCredentialRefs: ProviderCredentialRef[];
  failures: OnboardingFailure[];
  lastUpdatedAt: string;
};

export type OnboardingSelection = {
  workspaceId: UUID | null;
  sourceId: UUID | null;
  symbolIds: UUID[];
  timeframes: string[];
};

export type HealthCheckTarget = {
  workspaceId: UUID;
  sourceId: UUID | null;
  symbol: SymbolRead;
  timeframe: string;
  startTime: string;
  endTime: string;
};

export type HealthCheckInput = {
  target: HealthCheckTarget;
  latestFinalCandle: CandleRead | null;
  candleCount: CandleCountRead | null;
  candleQuality: CandleQualityReport | null;
  dataQualityRun: DataQualityRun | null;
  marketMemory: MarketMemorySnapshot | null;
  liveSubscription: LiveSubscription | null;
  providerPollingRequest: ProviderPollingRequest | null;
  errors: ApiError[];
};

export type DataHealthRow = HealthCheckInput & {
  status: DataHealthStatus;
  statusLabel: string;
  issues: string[];
};

export type GapDetectionRow = {
  health: DataHealthRow;
  plan: CandleGapRecoveryPlan | null;
  items: CandleGapRecoveryItem[];
  errors: ApiError[];
};

export type RecoveryPreparationRow = {
  gap: GapDetectionRow;
  preparation: PrepareProviderPollingResponse | null;
  requests: PreparedProviderPollingRequest[];
  errors: ApiError[];
};

export type OnboardingSummaryCounts = {
  ready: number;
  degraded: number;
  missingData: number;
  staleLiveFeeds: number;
  recoveryNeeded: number;
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

export type DataSourceCreate = {
  workspace_id: UUID;
  name: string;
  source_type: string;
  provider: string;
  status: string;
  credential_ref_id?: UUID | null;
  config_json: JsonRecord;
};

export type ProviderCredentialRef = {
  id: UUID;
  workspace_id: UUID;
  name: string;
  provider: string;
  credential_type: string;
  status: string;
  secret_ref_configured: boolean;
  secret_ref_summary: JsonRecord | null;
  public_metadata_json: JsonRecord;
  last_test_status: string | null;
  last_tested_at: string | null;
  last_error_message: string | null;
  rotated_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ProviderConnectionTest = {
  id: UUID;
  workspace_id: UUID;
  credential_ref_id: UUID | null;
  provider: string;
  test_type: string;
  status: string;
  request_metadata_json: JsonRecord;
  response_metadata_json: JsonRecord;
  error_message: string | null;
  created_at: string;
};

export type ProviderConfigurationTestCreate = {
  workspace_id: UUID;
  provider: string;
  credential_type: string;
  test_type: string;
  request_metadata_json?: JsonRecord;
};

export type CandleRead = {
  id: UUID;
  workspace_id: UUID;
  symbol_id: UUID;
  source_id: UUID;
  import_batch_id: UUID | null;
  live_feed_event_id: UUID | null;
  chart_screenshot_run_id: UUID | null;
  timeframe: string;
  timestamp: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string | null;
  is_final: boolean;
  quality_score: string | null;
  created_at: string;
  updated_at: string;
};

export type CandleCountRead = {
  count: number;
};

export type CandleQualityReport = {
  expected_candles: number;
  available_final_candles: number;
  available_partial_candles: number;
  missing_candles: number;
  duplicate_candles: number;
  quality_score: string;
  has_partial_latest_candle: boolean;
};

export type ProviderPollingRequest = {
  id: UUID;
  workspace_id: UUID;
  source_id: UUID;
  symbol_id: UUID;
  provider: string;
  provider_symbol: string;
  timeframe: string;
  start_time: string | null;
  end_time: string | null;
  limit: number | null;
  status: string;
  requested_url: string | null;
  request_metadata_json: JsonRecord;
  response_metadata_json: JsonRecord;
  received_candle_count: number;
  stored_candle_count: number;
  skipped_candle_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type LiveSubscription = {
  id: UUID;
  workspace_id: UUID;
  source_id: UUID;
  symbol_id: UUID;
  timeframe: string;
  provider: string;
  status: string;
  last_message_at: string | null;
  last_final_candle_at: string | null;
  last_error: string | null;
  worker_id: string | null;
  lease_expires_at: string | null;
  config_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type DataQualityRun = {
  id: UUID;
  workspace_id: UUID;
  scope_type: string;
  status: string;
  quality_version: string;
  symbol_id: UUID | null;
  source_id: UUID | null;
  live_subscription_id: UUID | null;
  timeframe: string | null;
  start_time: string | null;
  end_time: string | null;
  candle_count: number;
  finding_count: number;
  quality_score: string;
  quality_label: string;
  summary_json: JsonRecord;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type CandleGapRecoveryPlan = {
  id: UUID;
  workspace_id: UUID;
  symbol_id: UUID;
  source_id: UUID | null;
  timeframe: string;
  status: string;
  recovery_version: string;
  detection_start_time: string;
  detection_end_time: string;
  detected_gap_count: number;
  planned_request_count: number;
  completed_request_count: number;
  skipped_request_count: number;
  failed_request_count: number;
  summary: string;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type CandleGapRecoveryItem = {
  id: UUID;
  workspace_id: UUID;
  recovery_plan_id: UUID;
  symbol_id: UUID;
  source_id: UUID | null;
  timeframe: string;
  gap_start_time: string;
  gap_end_time: string;
  expected_candle_count: number;
  status: string;
  recovery_method: string;
  provider_polling_request_id: UUID | null;
  skip_reason: string | null;
  error_message: string | null;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type PreparedProviderPollingRequest = {
  recovery_item_id: UUID;
  provider_polling_request_id: UUID | null;
  status: string;
  recovery_method: string;
  provider: string | null;
  provider_symbol: string | null;
  source_id: UUID | null;
  timeframe: string;
  start_time: string;
  end_time: string;
  limit: number;
  expected_candle_count: number;
  skip_reason: string | null;
  error_message: string | null;
  request_metadata_json: JsonRecord;
};

export type PrepareProviderPollingResponse = {
  plan_id: UUID;
  create_requests: boolean;
  prepared_request_count: number;
  created_request_count: number;
  skipped_request_count: number;
  failed_request_count: number;
  requests: PreparedProviderPollingRequest[];
};
