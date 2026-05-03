import type { ApiFailure, JsonRecord, SymbolRead, UUID, Workspace } from "@/lib/api/types";

export type PreferenceProfileStatus = "active" | "paused" | "archived";

export type PreferenceProfile = {
  id: UUID;
  workspace_id: UUID;
  user_id: UUID | null;
  name: string;
  description: string | null;
  status: PreferenceProfileStatus;
  is_default: boolean;
  market_types_json: string[];
  symbol_ids_json: string[];
  excluded_symbol_ids_json: string[];
  timeframes_json: string[];
  session_labels_json: string[];
  pattern_types_json: string[];
  excluded_pattern_types_json: string[];
  strategy_profile_keys_json: string[];
  minimum_confidence: string | null;
  minimum_setup_quality: string | null;
  max_stale_seconds: number | null;
  require_fresh_data: boolean;
  require_timeframe_agreement: boolean;
  require_acceptable_data_quality: boolean;
  include_news_context: boolean;
  include_outcomes: boolean;
  notification_preferences_json: JsonRecord;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type StrategyProfileOption = {
  id: UUID;
  key: string;
  name: string;
  version: string;
  is_active: boolean;
};

export type PreferenceProfileInput = {
  workspace_id: UUID;
  user_id?: UUID;
  name: string;
  description?: string;
  is_default?: boolean;
  market_types_json: string[];
  symbol_ids_json: UUID[];
  excluded_symbol_ids_json: UUID[];
  timeframes_json: string[];
  session_labels_json: string[];
  pattern_types_json: string[];
  excluded_pattern_types_json: string[];
  strategy_profile_keys_json: string[];
  minimum_confidence?: number;
  minimum_setup_quality?: number;
  max_stale_seconds?: number;
  require_fresh_data: boolean;
  require_timeframe_agreement: boolean;
  require_acceptable_data_quality: boolean;
  include_news_context: boolean;
  include_outcomes: boolean;
  notification_preferences_json?: JsonRecord;
  metadata_json?: JsonRecord;
};

export type PreferenceProfileUpdateInput = Partial<Omit<PreferenceProfileInput, "workspace_id">> & {
  status?: PreferenceProfileStatus;
};

export type PreferenceProfileMatch = {
  profile_id: UUID;
  signal_id: UUID;
  matches: boolean;
  included_reasons: string[];
  excluded_reasons: string[];
  preference_warnings: string[];
};

export type PreferenceProfileFilterContext = {
  profile: PreferenceProfile;
  filters: JsonRecord;
  safety_boundaries: string[];
};

export type PreferenceProfilesFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type PreferenceProfilesPageData = {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: UUID | null;
  selectedProfileId: UUID | null;
  workspace: Workspace | null;
  workspaces: Workspace[];
  symbols: SymbolRead[];
  strategyProfiles: StrategyProfileOption[];
  profiles: PreferenceProfile[];
  selectedProfile: PreferenceProfile | null;
  filterContext: PreferenceProfileFilterContext | null;
  failures: PreferenceProfilesFailure[];
  lastUpdatedAt: string;
};

export const preferenceMarkets = ["forex", "crypto", "stock", "index", "commodity"] as const;
export const preferenceTimeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"] as const;
export const preferenceSessions = [
  "asia",
  "london",
  "new_york",
  "overlap",
  "off_hours",
  "unknown",
] as const;
export const preferencePatterns = [
  "bullish_breakout",
  "bearish_breakdown",
  "bullish_continuation",
  "bearish_continuation",
  "bullish_reversal",
  "bearish_reversal",
  "sideways_range",
  "low_volatility_chop",
  "fakeout",
  "unclear_structure",
] as const;

export function preferenceProfilesFailure(
  label: string,
  result: ApiFailure,
): PreferenceProfilesFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}
