import type { ApiError, UUID, Workspace } from "@/lib/api/types";

export type OnboardingReadinessLabel = "ready" | "needs_setup" | "degraded" | "blocked" | "unknown";
export type OnboardingStepState = "complete" | "incomplete" | "warning" | "blocked" | "unavailable";
export type OnboardingDataFreshnessLabel = "fresh" | "stale" | "no_data" | "unknown";

export type OnboardingActionType =
  | "create_workspace"
  | "create_user"
  | "seed_symbols"
  | "seed_default_data_sources"
  | "create_basic_watchlist"
  | "create_basic_scan_config"
  | "run_readiness_check"
  | "run_demo_flow";

export type OnboardingNextStepKey =
  | "create_workspace"
  | "create_user"
  | "seed_symbols"
  | "configure_data_source"
  | "verify_data"
  | "create_watchlist"
  | "create_scan_config"
  | "run_readiness"
  | "open_command_center"
  | "run_demo";

export type OnboardingStatus = {
  readiness_label: OnboardingReadinessLabel;
  readiness_score: number;
  summary: string;
};

export type OnboardingWorkspaceStatus = {
  exists: boolean;
  workspace_id: UUID | null;
  name: string | null;
};

export type OnboardingUserStatus = {
  exists: boolean;
  user_id: UUID | null;
  role: "admin" | "analyst" | "user" | string | null;
};

export type OnboardingCountStatus = {
  configured: boolean;
  count: number;
  missing: boolean;
};

export type OnboardingDataSourcesStatus = OnboardingCountStatus & {
  provider_ready: boolean;
};

export type OnboardingDataFreshnessStatus = {
  label: OnboardingDataFreshnessLabel;
  summary: string;
};

export type OnboardingDailyWorkflowStatus = {
  available: boolean;
  last_run_status: string | null;
};

export type OnboardingDemoModeStatus = {
  available: boolean;
  enabled: boolean;
};

export type OnboardingNextStep = {
  key: OnboardingNextStepKey;
  title: string;
  description: string;
  route: string;
  action_type: OnboardingActionType | null;
};

export type OnboardingStep = {
  key: string;
  title: string;
  description: string;
  state: OnboardingStepState;
  route: string;
  action_type: OnboardingActionType | null;
  metadata: Record<string, unknown>;
};

export type OnboardingStatusResponse = {
  status: OnboardingStatus;
  workspace: OnboardingWorkspaceStatus;
  user: OnboardingUserStatus;
  symbols: OnboardingCountStatus;
  data_sources: OnboardingDataSourcesStatus;
  data_freshness: OnboardingDataFreshnessStatus;
  watchlists: OnboardingCountStatus;
  scan_configs: OnboardingCountStatus;
  daily_workflow: OnboardingDailyWorkflowStatus;
  demo_mode: OnboardingDemoModeStatus;
  next_step: OnboardingNextStep;
  steps: OnboardingStep[];
  warnings: string[];
  missing_sections: string[];
};

export type OnboardingActionResponse = {
  action_type: OnboardingActionType;
  status: string;
  message: string;
  workspace_id: UUID | null;
  user_id: UUID | null;
  artifact_ids: Record<string, UUID | UUID[] | null>;
  onboarding_status: OnboardingStatusResponse | null;
};

export type OnboardingPageData = {
  appName: string;
  status: OnboardingStatusResponse | null;
  statusError: ApiError | null;
  workspaces: Workspace[];
  selectedWorkspaceId: UUID | null;
};
