import type { ApiError } from "@/lib/api/types";
import type { WorkspaceOverview, WorkspaceQuickActionResponse } from "@/lib/command-center/overviewTypes";

export type DailyWorkflowActionType =
  | "run_daily_workflow"
  | "refresh_provider_health"
  | "generate_daily_brief"
  | "score_recent_signals"
  | "refresh_market_memory"
  | "run_product_readiness";

export type WorkspaceOverviewState = {
  overview: WorkspaceOverview | null;
  loading: boolean;
  lastRefreshedAt: string | null;
  error: ApiError | null;
};

export type WorkspaceQuickActionState = {
  pendingAction: DailyWorkflowActionType | null;
  latestResult: WorkspaceQuickActionResponse | null;
  error: ApiError | null;
};
