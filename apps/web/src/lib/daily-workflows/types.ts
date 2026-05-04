import type { JsonRecord, UUID } from "@/lib/api/types";

export type DailyWorkflowStatus = "pending" | "running" | "completed" | "completed_with_warnings" | "failed" | "cancelled";

export type DailyWorkflowStepStatus = "pending" | "running" | "completed" | "skipped" | "failed" | "cancelled";

export type DailyWorkflowOptions = {
  prepare_gap_recovery: boolean;
  allow_provider_polling: boolean;
  run_scan: boolean;
  generate_setup_context: boolean;
  score_priorities: boolean;
  generate_digest: boolean;
  generate_brief: boolean;
  force?: boolean;
};

export type DailyWorkflowRunRequest = {
  workspace_id: UUID;
  workflow_type: "daily_scan" | "session_scan" | "watchlist_scan" | "data_refresh_only";
  watchlist_id?: UUID;
  preference_profile_id?: UUID | null;
  period_start?: string;
  period_end?: string;
  options: DailyWorkflowOptions;
  filters_json?: JsonRecord;
};

export type DailyWorkflowRun = {
  id: UUID;
  workspace_id: UUID;
  workflow_type: string;
  status: DailyWorkflowStatus;
  workflow_version: string;
  watchlist_id: UUID | null;
  preference_profile_id: UUID | null;
  period_start: string | null;
  period_end: string | null;
  filters_json: JsonRecord;
  steps_json: JsonRecord[];
  result_json: JsonRecord;
  created_artifact_ids_json: JsonRecord;
  summary: string;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type DailyWorkflowStep = {
  id: UUID;
  workspace_id: UUID;
  workflow_run_id: UUID;
  step_key: string;
  status: DailyWorkflowStepStatus;
  started_at: string | null;
  completed_at: string | null;
  input_json: JsonRecord;
  output_json: JsonRecord | null;
  skipped_reason: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type DailyWorkflowFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};
