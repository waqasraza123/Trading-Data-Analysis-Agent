import type { ApiFailure, JsonRecord, SymbolRead, UUID, Workspace } from "@/lib/api/types";
import type {
  EquityDataFailure,
  EquityDataProviderCapability,
  EquityDataProviderRequest,
  EquityEarningsEvent,
  EquityFundamentalSnapshot,
  EquitySymbolMetadataSnapshot,
} from "@/lib/equity-data/types";
import type { ProviderCredentialRef } from "@/lib/data-onboarding/types";

export type EquityUniverse = {
  id: UUID;
  workspace_id: UUID;
  name: string;
  description: string | null;
  status: string;
  universe_type: string;
  filters_json: JsonRecord;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type EquityUniverseMember = {
  id: UUID;
  workspace_id: UUID;
  universe_id: UUID;
  symbol_id: UUID;
  ticker: string;
  company_name: string | null;
  sector: string | null;
  industry: string | null;
  exchange: string | null;
  market_cap: string | null;
  average_volume: string | null;
  is_active: boolean;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type EquitySwingScanRun = {
  id: UUID;
  workspace_id: UUID;
  universe_id: UUID | null;
  watchlist_id: UUID | null;
  status: string;
  scan_version: string;
  scan_profile_key: string;
  filters_json: JsonRecord;
  scanned_symbol_count: number;
  candidate_count: number;
  rejected_count: number;
  summary: string;
  error_message: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type EquitySwingCandidate = {
  id: UUID;
  workspace_id: UUID;
  scan_run_id: UUID;
  symbol_id: UUID;
  timeframe: string;
  candidate_status: string;
  setup_type: string;
  directional_bias: string;
  setup_quality_score: string;
  setup_quality_label: string;
  liquidity_score: string | null;
  volume_score: string | null;
  trend_quality_score: string | null;
  pullback_quality_score: string | null;
  relative_strength_score: string | null;
  momentum_score: string | null;
  volatility_score: string | null;
  catalyst_score: string | null;
  confidence_context_json: JsonRecord;
  evidence_json: JsonRecord[];
  risk_notes_json: JsonRecord[];
  setup_context_id: UUID | null;
  signal_id: UUID | null;
  analysis_run_id: UUID | null;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type EquityCatalystContext = {
  id: UUID;
  workspace_id: UUID;
  symbol_id: UUID;
  source_type: string;
  event_time: string | null;
  catalyst_type: string;
  title: string;
  summary: string;
  importance: string;
  sentiment: string;
  raw_reference_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type EquityResearchFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type EquityResearchData = {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: UUID | null;
  workspace: Workspace | null;
  workspaces: Workspace[];
  stockSymbols: SymbolRead[];
  universes: EquityUniverse[];
  selectedUniverse: EquityUniverse | null;
  selectedUniverseMembers: EquityUniverseMember[];
  scanRuns: EquitySwingScanRun[];
  selectedScanRun: EquitySwingScanRun | null;
  candidates: EquitySwingCandidate[];
  selectedCandidate: EquitySwingCandidate | null;
  catalysts: EquityCatalystContext[];
  equityDataProviders: EquityDataProviderCapability[];
  providerRequests: EquityDataProviderRequest[];
  selectedMetadata: EquitySymbolMetadataSnapshot | null;
  selectedFundamentals: EquityFundamentalSnapshot | null;
  selectedEarnings: EquityEarningsEvent[];
  providerCredentialRefs: ProviderCredentialRef[];
  equityDataFailures: EquityDataFailure[];
  failures: EquityResearchFailure[];
  lastUpdatedAt: string;
};

export type EquityUniverseCreateInput = {
  workspace_id: UUID;
  name: string;
  description?: string;
  universe_type: "manual" | "market_cap" | "sector" | "index" | "watchlist_linked" | "custom";
};

export type EquityUniverseMemberCreateInput = {
  symbol_id: UUID;
  average_volume?: number;
  sector?: string;
  exchange?: string;
};

export type EquitySwingScanInput = {
  workspace_id: UUID;
  universe_id?: UUID;
  scan_profile_key: string;
  timeframes: string[];
  filters: {
    min_average_volume?: number;
    min_setup_score?: number;
    max_symbols?: number;
  };
  options: {
    use_existing_analysis_only: boolean;
    generate_setup_context: boolean;
    score_signal_priority: boolean;
  };
};

export type EquityCatalystCreateInput = {
  workspace_id: UUID;
  symbol_id: UUID;
  source_type: string;
  event_time?: string;
  catalyst_type: string;
  title: string;
  summary: string;
  importance: string;
  sentiment: string;
};

export function equityFailure(label: string, result: ApiFailure): EquityResearchFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}
