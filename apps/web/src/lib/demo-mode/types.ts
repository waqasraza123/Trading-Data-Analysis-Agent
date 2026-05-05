import type { UUID } from "@/lib/api/types";

export type DemoModeStatus = {
  enabled: boolean;
  status: string;
  app_env: string;
  reason: string | null;
  default_workspace_name: string;
  default_symbols: string[];
  default_timeframes: string[];
  safety_notices: string[];
};

export type DemoModeArtifactLink = {
  label: string;
  href: string;
  artifact_type: string;
  artifact_id: string | null;
};

export type DemoModeFlowStep = {
  key: string;
  status: string;
  summary: string;
  metadata: Record<string, unknown>;
};

export type DemoModeRunFullFlow = {
  enabled: boolean;
  status: string;
  message: string;
  workspace_id: UUID | null;
  user_id: UUID | null;
  source_id: UUID | null;
  symbols: Record<string, unknown>[];
  timeframes: string[];
  links: DemoModeArtifactLink[];
  safety_notices: string[];
  import_batch_ids: UUID[];
  analysis_run_ids: UUID[];
  signal_ids: UUID[];
  setup_context_ids: UUID[];
  priority_score_ids: UUID[];
  outcome_ids: UUID[];
  watchlist_id: UUID | null;
  scan_config_id: UUID | null;
  scan_run_id: UUID | null;
  daily_brief_id: UUID | null;
  journal_entry_id: UUID | null;
  readiness_run_id: UUID | null;
  steps: DemoModeFlowStep[];
};
