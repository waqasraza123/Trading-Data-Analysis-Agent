import type { ApiError, JsonRecord, UUID } from "@/lib/api/types";

export type ProviderHealthStatus =
  | "healthy"
  | "degraded"
  | "stale"
  | "failing"
  | "unavailable"
  | "unknown";

export type ProviderHealthFreshnessLabel = "fresh" | "delayed" | "stale" | "no_data" | "unknown";

export type ProviderHealthSnapshot = {
  id: UUID;
  workspace_id: UUID;
  source_id: UUID;
  provider: string;
  symbol_id: UUID | null;
  timeframe: string | null;
  status: ProviderHealthStatus;
  freshness_label: ProviderHealthFreshnessLabel;
  latest_final_candle_time: string | null;
  latest_successful_poll_at: string | null;
  latest_failed_poll_at: string | null;
  latest_gap_recovery_plan_id: UUID | null;
  latest_data_quality_run_id: UUID | null;
  consecutive_failure_count: number;
  missing_candle_count: number;
  stale_seconds: number | null;
  summary: string;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type ProviderHealthSummary = {
  workspace_id: UUID;
  total_snapshots: number;
  healthy_count: number;
  degraded_count: number;
  stale_count: number;
  failing_count: number;
  unavailable_count: number;
  unknown_count: number;
  fresh_count: number;
  delayed_count: number;
  no_data_count: number;
  missing_candle_count: number;
  provider_failure_count: number;
  ready_for_deterministic_analysis_count: number;
  latest_snapshot_at: string | null;
};

export type ProviderHealthWorkspaceRefreshResponse = {
  workspace_id: UUID;
  requested_limit: number;
  refreshed_count: number;
  skipped_count: number;
  snapshots: ProviderHealthSnapshot[];
};

export type ProviderHealthPrepareGapRecoveryResponse = {
  snapshot: ProviderHealthSnapshot;
  recovery_plan: {
    id: UUID;
    detected_gap_count: number;
    planned_request_count: number;
    skipped_request_count: number;
    failed_request_count: number;
    summary: string;
    status: string;
  } | null;
  preparation: {
    plan_id: UUID;
    create_requests: boolean;
    prepared_request_count: number;
    created_request_count: number;
    skipped_request_count: number;
    failed_request_count: number;
    requests: Array<{
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
    }>;
  } | null;
  created_plan: boolean;
};

export type ProviderHealthFailure = ApiError;
