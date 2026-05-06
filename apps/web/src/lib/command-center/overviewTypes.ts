import type { JsonRecord, JsonValue, UUID } from "@/lib/api/types";

export type WorkspaceOverviewStatus = {
  status: string;
  label: string;
  summary: string;
  metadata_json: JsonRecord;
};

export type WorkspaceOverviewItem = {
  id: string;
  title: string;
  summary: string;
  reason: string | null;
  symbol_id: UUID | null;
  symbol: string | null;
  timeframe: string | null;
  signal_id: UUID | null;
  analysis_run_id: UUID | null;
  bias: string | null;
  confidence_label: string | null;
  priority_label: string | null;
  setup_quality_label: string | null;
  freshness_label: string | null;
  data_quality_label: string | null;
  href: string | null;
  metadata_json: JsonRecord;
};

export type WorkspaceOverviewNotificationSummary = {
  unread_count: number;
  acknowledged_count: number;
  latest: WorkspaceOverviewItem[];
  metadata_json: JsonRecord;
};

export type WorkspaceOverview = {
  workspace_id: UUID;
  generated_at: string;
  overview_version: string;
  readiness: WorkspaceOverviewStatus;
  data_freshness: WorkspaceOverviewStatus;
  provider_health: WorkspaceOverviewStatus;
  daily_brief: WorkspaceOverviewStatus;
  workflow: WorkspaceOverviewStatus;
  review_first: WorkspaceOverviewItem[];
  needs_confirmation: WorkspaceOverviewItem[];
  avoid_conditions: WorkspaceOverviewItem[];
  outcome_updates: WorkspaceOverviewItem[];
  pending_actions: WorkspaceOverviewItem[];
  notifications: WorkspaceOverviewNotificationSummary;
  journal_prompts: WorkspaceOverviewItem[];
  quality_warnings: WorkspaceOverviewItem[];
  navigation_hints: WorkspaceOverviewItem[];
  missing_sections: string[];
  warnings: string[];
};

export type WorkspaceQuickActionRequest = {
  action_type: string;
  watchlist_id?: UUID | null;
  preference_profile_id?: UUID | null;
  options?: Record<string, JsonValue | undefined>;
};

export type WorkspaceQuickActionResponse = {
  workspace_id: UUID;
  action_type: string;
  status: string;
  summary: string;
  created_artifact_ids_json: JsonRecord;
  result_json: JsonRecord;
  warnings: string[];
  missing_sections: string[];
};
