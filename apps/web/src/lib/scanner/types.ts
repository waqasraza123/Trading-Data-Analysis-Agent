import type {
  ApiFailure,
  HealthResponse,
  JsonRecord,
  ScheduledScanConfig,
  SignalClassification,
  SymbolRead,
  UUID,
  Watchlist,
  WatchlistItem,
  WorkerStatusResponse,
  Workspace,
} from "@/lib/api/types";
import type { DailyWorkflowFailure, DailyWorkflowRun, DailyWorkflowStep } from "@/lib/daily-workflows/types";

export type ScannerFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type WatchlistWithItems = {
  watchlist: Watchlist;
  items: WatchlistItem[];
};

export type ScannerDataSource = {
  id: UUID;
  workspace_id: UUID;
  name: string;
  source_type: string;
  provider: string;
  status: string;
  config_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type ScheduledScanRun = {
  id: UUID;
  workspace_id: UUID;
  scan_config_id: UUID;
  status: string;
  scan_mode: string;
  scheduled_for: string | null;
  started_at: string | null;
  completed_at: string | null;
  scanned_item_count: number;
  analysis_run_count: number;
  skipped_count: number;
  failed_count: number;
  analysis_run_ids_json: string[];
  signal_ids_json: string[];
  reasoning_run_ids_json: string[] | null;
  action_plan_ids_json: string[] | null;
  result_json: JsonRecord;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type ScheduledScanRunItem = {
  id: UUID;
  workspace_id: UUID;
  scan_run_id: UUID;
  scan_config_id: UUID;
  watchlist_item_id: UUID | null;
  symbol_id: UUID;
  source_id: UUID | null;
  timeframe: string;
  status: string;
  analysis_run_id: UUID | null;
  signal_id: UUID | null;
  reasoning_run_id: UUID | null;
  action_plan_id: UUID | null;
  skipped_reason: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type ScannerPreset = {
  id: UUID;
  workspace_id: UUID | null;
  key: string;
  name: string;
  description: string;
  category: string;
  status: string;
  preset_version: string;
  market_types_json: string[];
  symbol_templates_json: JsonRecord[];
  timeframe_templates_json: string[];
  session_filters_json: JsonRecord;
  scan_config_template_json: JsonRecord;
  watchlist_template_json: JsonRecord;
  preference_profile_filters_json: JsonRecord;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type ScannerPresetApplication = {
  id: UUID;
  workspace_id: UUID;
  scanner_preset_id: UUID;
  status: "completed" | "completed_with_warnings" | "failed";
  watchlist_id: UUID | null;
  scan_config_id: UUID | null;
  preference_profile_id: UUID | null;
  applied_config_json: JsonRecord;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type ScannerPresetApplyInput = {
  workspace_id: UUID;
  symbol_ids: UUID[];
  source_id?: UUID;
  timeframes: string[];
  create_watchlist: boolean;
  create_scan_config: boolean;
  name_override?: string;
};

export type ScannerPresetSeedResponse = {
  seeded_count: number;
  presets: ScannerPreset[];
};

export type RunDueScansResponse = {
  run_count: number;
  runs: ScheduledScanRun[];
};

export type ScannerData = {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: UUID | null;
  selectedRunId: UUID | null;
  selectedWorkflowRunId: UUID | null;
  workspace: Workspace | null;
  workspaces: Workspace[];
  symbols: SymbolRead[];
  dataSources: ScannerDataSource[];
  presets: ScannerPreset[];
  watchlists: WatchlistWithItems[];
  scanConfigs: ScheduledScanConfig[];
  dueScanConfigs: ScheduledScanConfig[];
  recentRuns: ScheduledScanRun[];
  selectedRun: ScheduledScanRun | null;
  selectedRunItems: ScheduledScanRunItem[];
  selectedRunSignals: SignalClassification[];
  dailyWorkflowRuns: DailyWorkflowRun[];
  selectedDailyWorkflowRun: DailyWorkflowRun | null;
  selectedDailyWorkflowSteps: DailyWorkflowStep[];
  health: HealthResponse | null;
  workerStatus: WorkerStatusResponse | null;
  failures: ScannerFailure[];
  dailyWorkflowFailures: DailyWorkflowFailure[];
  lastUpdatedAt: string;
};

export type ScannerMutationState = {
  status: "idle" | "pending" | "success" | "error";
  message: string | null;
};

export type WatchlistCreateInput = {
  workspace_id: UUID;
  name: string;
  description?: string;
};

export type WatchlistUpdateInput = {
  status?: "active" | "paused" | "archived";
};

export type WatchlistItemCreateInput = {
  symbol_id: UUID;
  source_id?: UUID;
  timeframe: string;
  include_partial_live_candle: boolean;
};

export type WatchlistItemUpdateInput = {
  is_active?: boolean;
};

export type ScheduledScanConfigCreateInput = {
  workspace_id: UUID;
  name: string;
  description?: string;
  watchlist_id?: UUID;
  symbol_id?: UUID;
  source_id?: UUID;
  timeframe?: string;
  scan_mode: "watchlist" | "single_symbol";
  lookback_minutes: number;
  interval_seconds: number;
  include_partial_live_candle: boolean;
  include_news_correlation: boolean;
  include_ai_explanation: boolean;
  include_reasoning: boolean;
  include_action_plan: boolean;
};

export type ScheduledScanConfigUpdateInput = {
  status?: "active" | "paused" | "archived";
};

export type RunDueScansInput = {
  workspace_id?: UUID;
  limit: number;
};

export type ScannerActionResult =
  | RunDueScansResponse
  | ScannerPresetApplication
  | ScheduledScanRun
  | ScheduledScanConfig
  | Watchlist
  | WatchlistItem;

export function scannerFailure(label: string, result: ApiFailure): ScannerFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}
