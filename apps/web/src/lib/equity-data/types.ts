import type { ApiFailure, JsonRecord, UUID } from "@/lib/api/types";

export type EquityDataProviderCapability = {
  provider: string;
  label: string;
  configured: boolean;
  external_requests_enabled: boolean;
  requires_credential_ref: boolean;
  supports_universe_import: boolean;
  supports_metadata_lookup: boolean;
  supports_fundamentals_snapshot: boolean;
  supports_earnings_calendar: boolean;
  status: string;
  message: string;
};

export type EquityDataProviderRequest = {
  id: UUID;
  workspace_id: UUID;
  provider: string;
  request_type: string;
  status: string;
  credential_ref_id: UUID | null;
  universe_id: UUID | null;
  symbol_id: UUID | null;
  ticker: string | null;
  request_json: JsonRecord;
  response_summary_json: JsonRecord;
  received_count: number;
  stored_count: number;
  skipped_count: number;
  failed_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type EquityDataOperation = {
  id: UUID;
  operation_id: UUID;
  workspace_id: UUID;
  operation_type: string;
  provider_name: string | null;
  status: string;
  requested_by_user_id: UUID | null;
  idempotency_key: string | null;
  progress_current: number;
  progress_total: number | null;
  progress_message: string | null;
  counters_json: JsonRecord;
  request_summary_json: JsonRecord;
  result_summary_json: JsonRecord;
  error_summary_json: JsonRecord;
  linked_provider_request_id: UUID | null;
  linked_job_id: UUID | null;
  dry_run: boolean;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type EquityDataImportError = {
  id: UUID;
  workspace_id: UUID;
  provider_request_id: UUID;
  row_number: number | null;
  error_code: string;
  error_message: string;
  raw_item_json: JsonRecord | null;
  created_at: string;
};

export type EquityDataOperationDetail = EquityDataOperation & {
  recent_errors: EquityDataImportError[];
};

export type EquityDataOperationDiagnosticItem = {
  source: string;
  event_type: string;
  status: string | null;
  message: string;
  occurred_at: string;
  metadata_json: JsonRecord;
};

export type EquityDataOperationLinkedJob = {
  id: UUID;
  workspace_id: UUID | null;
  queue_name: string;
  job_type: string;
  status: string;
  priority: string;
  idempotency_key: string | null;
  scheduled_at: string | null;
  available_at: string | null;
  locked_by: string | null;
  locked_until: string | null;
  attempts: number;
  max_attempts: number;
  payload_json: JsonRecord;
  result_json: JsonRecord | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export type EquityDataOperationJobEvent = {
  id: UUID;
  workspace_id: UUID | null;
  job_id: UUID;
  event_type: string;
  message: string;
  metadata_json: JsonRecord;
  created_at: string;
};

export type EquityDataOperationDiagnostics = {
  operation: EquityDataOperation;
  linked_job: EquityDataOperationLinkedJob | null;
  linked_provider_request: EquityDataProviderRequest | null;
  job_events: EquityDataOperationJobEvent[];
  recent_errors: EquityDataImportError[];
  timeline: EquityDataOperationDiagnosticItem[];
};

export type EquityDataOperationLineageNode = {
  operation: EquityDataOperation;
  relationship: string;
  depth: number;
  retry_of_operation_id: UUID | null;
  retry_reason: string | null;
  can_retry: boolean;
  can_cancel: boolean;
};

export type EquityDataOperationLineage = {
  operation: EquityDataOperation;
  root_operation: EquityDataOperation;
  source_operations: EquityDataOperationLineageNode[];
  retry_operations: EquityDataOperationLineageNode[];
  lineage: EquityDataOperationLineageNode[];
  scanned_count: number;
  scan_limit: number;
};

export type EquityDataOperationSummary = {
  workspace_id: UUID;
  total_count: number;
  active_count: number;
  terminal_count: number;
  warning_count: number;
  failed_count: number;
  cancelled_count: number;
  latest_operation_at: string | null;
  status_counts: Record<string, number>;
  operation_type_counts: Record<string, number>;
  provider_counts: Record<string, number>;
  recent_problem_operations: EquityDataOperation[];
};

export type EquityDataOperationReviewItem = {
  operation: EquityDataOperation;
  review_reason: string;
  recommended_action: string;
  severity: string;
  can_retry: boolean;
  can_cancel: boolean;
  stale_after_minutes: number;
  last_update_at: string;
};

export type EquityDataOperationReviewQueue = {
  workspace_id: UUID;
  stale_after_minutes: number;
  total_count: number;
  retryable_count: number;
  cancellable_count: number;
  items: EquityDataOperationReviewItem[];
};

export type EquityDataOperationAuditSection = {
  key: string;
  label: string;
  status: string;
  summary: string;
  count: number | null;
};

export type EquityDataOperationRetryReadiness = {
  operation: EquityDataOperation;
  inspected_at: string;
  requested_run_mode: "sync" | "queued" | "auto";
  can_retry: boolean;
  retryable_status: boolean;
  payload_replayable: boolean;
  provider_ready: boolean;
  can_run_sync: boolean;
  replay_source: string;
  operation_type: string | null;
  provider_name: string | null;
  row_count: number | null;
  blockers: string[];
  warnings: string[];
};

export type EquityDataOperationAuditBundle = {
  generated_at: string;
  operation: EquityDataOperationDetail;
  diagnostics: EquityDataOperationDiagnostics;
  lineage: EquityDataOperationLineage;
  retry_readiness: EquityDataOperationRetryReadiness;
  review_item: EquityDataOperationReviewItem | null;
  sections: EquityDataOperationAuditSection[];
  error_limit: number;
  scan_limit: number;
  stale_after_minutes: number;
};

export type EquityDataOperationList = {
  operations: EquityDataOperation[];
};

export type EquityDataOperationCancelInput = {
  reason?: string;
};

export type EquityDataOperationRetryInput = {
  runMode?: "sync" | "queued" | "auto";
  idempotencyKey?: string;
  reason?: string;
};

export type EquityDataOperationInput = {
  workspaceId: UUID;
  provider?: string;
  credentialRefId?: UUID;
  universeId?: UUID;
  symbolIds?: UUID[];
  filters?: JsonRecord;
  limit?: number;
  runMode?: "sync" | "queued" | "auto";
  dryRun?: boolean;
  idempotencyKey?: string;
};

export type EquityFileImportResult = {
  run_mode: "sync" | "queued" | "auto";
  operation: EquityDataOperation | null;
  provider_request: EquityDataProviderRequest | null;
  validation_errors: unknown[];
  rows_received: number;
  rows_valid: number;
};

export type EquitySymbolMetadataSnapshot = {
  id: UUID;
  workspace_id: UUID;
  symbol_id: UUID;
  ticker: string;
  provider: string;
  company_name: string | null;
  exchange: string | null;
  sector: string | null;
  industry: string | null;
  country: string | null;
  currency: string | null;
  market_cap: string | null;
  average_volume: string | null;
  shares_float: string | null;
  is_etf: boolean | null;
  is_active: boolean;
  snapshot_time: string;
  raw_reference_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type EquityFundamentalSnapshot = {
  id: UUID;
  workspace_id: UUID;
  symbol_id: UUID;
  provider: string;
  snapshot_time: string;
  market_cap: string | null;
  average_volume: string | null;
  relative_volume: string | null;
  beta: string | null;
  pe_ratio: string | null;
  eps: string | null;
  revenue_growth: string | null;
  earnings_growth: string | null;
  debt_to_equity: string | null;
  free_cash_flow: string | null;
  raw_reference_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type EquityEarningsEvent = {
  id: UUID;
  workspace_id: UUID;
  symbol_id: UUID;
  provider: string;
  event_date: string;
  fiscal_period: string | null;
  report_time: string | null;
  eps_estimate: string | null;
  eps_actual: string | null;
  revenue_estimate: string | null;
  revenue_actual: string | null;
  importance: string;
  status: string;
  raw_reference_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type EquityImportRowInput = {
  ticker: string;
  companyName?: string;
  exchange?: string;
  sector?: string;
  industry?: string;
  marketCap?: string;
  averageVolume?: string;
};

export type EquityUniverseRowsImportInput = {
  workspaceId: UUID;
  universeId?: UUID;
  createUniverseName?: string;
  rows: EquityImportRowInput[];
};

export type EquityProviderUniverseImportInput = {
  workspaceId: UUID;
  provider: string;
  credentialRefId?: UUID;
  universeId?: UUID;
  createUniverseName?: string;
  filters: JsonRecord;
};

export type EquitySymbolEnrichmentInput = {
  workspaceId: UUID;
  provider?: string;
  credentialRefId?: UUID;
  filters?: JsonRecord;
};

export type EquityDataFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export function equityDataFailure(label: string, result: ApiFailure): EquityDataFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}
