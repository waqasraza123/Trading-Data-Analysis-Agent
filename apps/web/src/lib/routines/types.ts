import type { JsonRecord, UUID } from "@/lib/api/types";

export type DailyRoutineTemplateStatus = "active" | "archived";
export type DailyRoutineType = "pre_market" | "session_open" | "intraday" | "close_of_day" | "data_repair" | "review" | "custom";
export type DailyRoutineRunStatus = "pending" | "running" | "completed" | "completed_with_warnings" | "failed" | "cancelled";
export type DailyRoutineStepStatus = "pending" | "running" | "completed" | "skipped" | "failed";

export type DailyRoutineTemplate = {
  id: UUID;
  workspace_id: UUID | null;
  key: string;
  name: string;
  description: string;
  status: DailyRoutineTemplateStatus;
  routine_version: string;
  routine_type: DailyRoutineType;
  steps_json: JsonRecord[];
  default_filters_json: JsonRecord;
  schedule_hint_json: JsonRecord;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type DailyRoutineRunRequest = {
  workspace_id: UUID;
  input_json?: JsonRecord;
  enable_notifications?: boolean;
  force?: boolean;
  allow_provider_polling?: boolean;
  watchlist_id?: UUID | null;
  preference_profile_id?: UUID | null;
  period_start?: string;
  period_end?: string;
};

export type DailyRoutineRun = {
  id: UUID;
  workspace_id: UUID;
  template_id: UUID;
  status: DailyRoutineRunStatus;
  routine_version: string;
  input_json: JsonRecord;
  step_results_json: JsonRecord[];
  created_artifact_ids_json: JsonRecord;
  summary: string;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type DailyRoutineRunStep = {
  id: UUID;
  workspace_id: UUID;
  routine_run_id: UUID;
  step_key: string;
  status: DailyRoutineStepStatus;
  input_json: JsonRecord;
  output_json: JsonRecord | null;
  skipped_reason: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type DailyRoutineFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};
