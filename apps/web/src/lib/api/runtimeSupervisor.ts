import { apiGet, apiPost } from "./client";
import type { ApiResult, JsonRecord, UUID } from "./types";

export type RuntimeWorkerType =
  | "live_feed"
  | "stale_monitor"
  | "reasoning_actions"
  | "market_scans"
  | "provider_polling"
  | "notification_delivery"
  | "data_retention"
  | "backfill"
  | "metrics"
  | "custom";

export type RuntimeWorkerDefinitionStatus = "available" | "disabled" | "deprecated" | "unavailable";
export type RuntimeWorkerInstanceStatus = "starting" | "running" | "stale" | "stopped" | "failed" | "unknown";
export type RuntimeRunRequestStatus =
  | "pending"
  | "running"
  | "completed"
  | "completed_with_warnings"
  | "failed"
  | "cancelled"
  | "unsupported";

export type RuntimeWorkerDefinition = {
  id: UUID;
  key: string;
  name: string;
  description: string;
  worker_type: RuntimeWorkerType;
  status: RuntimeWorkerDefinitionStatus;
  command: string;
  required_settings_json: string[];
  optional_settings_json: string[];
  safety_notes_json: string[];
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type RuntimeWorkerInstance = {
  id: UUID;
  workspace_id: UUID | null;
  worker_definition_key: string;
  worker_id: string;
  status: RuntimeWorkerInstanceStatus;
  host_name: string | null;
  process_id: number | null;
  started_at: string | null;
  last_heartbeat_at: string | null;
  stopped_at: string | null;
  heartbeat_payload_json: JsonRecord;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type RuntimeHealthWorkerSummary = {
  key: string;
  name: string;
  worker_type: RuntimeWorkerType;
  definition_status: RuntimeWorkerDefinitionStatus;
  enabled: boolean;
  running_instances: number;
  stale_instances: number;
  last_heartbeat_at: string | null;
  pending_run_requests: number;
  running_run_requests: number;
  failed_run_requests: number;
};

export type RuntimeSupervisorHealth = {
  status: string;
  supervisor_version: string;
  heartbeat_enabled: boolean;
  run_requests_enabled: boolean;
  stale_after_seconds: number;
  worker_count: number;
  available_worker_count: number;
  disabled_worker_count: number;
  running_instance_count: number;
  stale_instance_count: number;
  pending_run_request_count: number;
  running_run_request_count: number;
  failed_run_request_count: number;
  workers: RuntimeHealthWorkerSummary[];
  operation_counts: Record<string, Record<string, number>>;
};

export type RuntimeRunRequest = {
  id: UUID;
  workspace_id: UUID | null;
  worker_definition_key: string;
  status: RuntimeRunRequestStatus;
  requested_by_user_id: UUID | null;
  request_type: string;
  input_json: JsonRecord;
  result_json: JsonRecord | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export function getRuntimeSupervisorHealth(
  workspaceId?: UUID | null,
): Promise<ApiResult<RuntimeSupervisorHealth>> {
  return apiGet<RuntimeSupervisorHealth>("/runtime-supervisor/health", {
    query: { workspace_id: workspaceId || undefined },
    optional: true,
    timeoutMs: 5000,
  });
}

export function listRuntimeWorkers(): Promise<ApiResult<RuntimeWorkerDefinition[]>> {
  return apiGet<RuntimeWorkerDefinition[]>("/runtime-supervisor/workers", {
    optional: true,
    timeoutMs: 5000,
  });
}

export function listRuntimeInstances(params: {
  workspaceId?: UUID | null;
  workerDefinitionKey?: string;
  status?: RuntimeWorkerInstanceStatus;
} = {}): Promise<ApiResult<RuntimeWorkerInstance[]>> {
  return apiGet<RuntimeWorkerInstance[]>("/runtime-supervisor/instances", {
    query: {
      workspace_id: params.workspaceId || undefined,
      worker_definition_key: params.workerDefinitionKey,
      status: params.status,
    },
    optional: true,
    timeoutMs: 5000,
  });
}

export function createRuntimeRunRequest(body: {
  workerDefinitionKey: string;
  requestType: "run_once" | "execute_due" | "refresh_status" | "dry_run";
  workspaceId?: UUID | null;
  requestedByUserId?: UUID | null;
  inputJson?: JsonRecord;
}): Promise<ApiResult<RuntimeRunRequest>> {
  return apiPost<RuntimeRunRequest>("/runtime-supervisor/run-requests", body, {
    optional: true,
    timeoutMs: 15000,
  });
}
