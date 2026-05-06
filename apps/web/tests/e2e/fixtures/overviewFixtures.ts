import type {
  WorkspaceOverview,
  WorkspaceOverviewItem,
  WorkspaceQuickActionResponse,
} from "../../../src/lib/command-center/overviewTypes";
import { demoWorkspaceId } from "./workspaceFixtures";

export const overviewSignalId = "33333333-3333-4333-8333-333333333333";

function item(input: Partial<WorkspaceOverviewItem> & Pick<WorkspaceOverviewItem, "id" | "title" | "summary">): WorkspaceOverviewItem {
  return {
    reason: "Review recommended.",
    symbol_id: null,
    symbol: "EURUSD",
    timeframe: "1m",
    signal_id: overviewSignalId,
    analysis_run_id: null,
    bias: "no directional signal",
    confidence_label: "medium",
    priority_label: "review recommended",
    setup_quality_label: "review recommended",
    freshness_label: "data fresh",
    data_quality_label: "outcome ready",
    href: `/signals/${overviewSignalId}`,
    metadata_json: {},
    ...input,
  };
}

export const readyWorkspaceOverview: WorkspaceOverview = {
  workspace_id: demoWorkspaceId,
  generated_at: "2026-05-06T08:00:00.000Z",
  overview_version: "e2e-smoke",
  readiness: {
    status: "ready",
    label: "Command center ready",
    summary: "Workspace is ready for deterministic analysis.",
    metadata_json: {},
  },
  data_freshness: {
    status: "fresh",
    label: "Data fresh",
    summary: "Fresh data contexts are available.",
    metadata_json: {
      freshCount: 2,
      staleOrDegradedCount: 0,
    },
  },
  provider_health: {
    status: "healthy",
    label: "Provider context healthy",
    summary: "No provider issues in the smoke fixture.",
    metadata_json: {
      missingCandleCount: 0,
    },
  },
  daily_brief: {
    status: "completed",
    label: "Brief ready",
    summary: "Brief context is available.",
    metadata_json: {},
  },
  workflow: {
    status: "completed",
    label: "Workflow ready",
    summary: "Daily workflow context is available.",
    metadata_json: {
      staleInstanceCount: 0,
    },
  },
  review_first: [
    item({
      id: "review-first-1",
      title: "Review first context",
      summary: "Setup context is ready for review.",
    }),
  ],
  needs_confirmation: [
    item({
      id: "needs-confirmation-1",
      title: "Confirmation context",
      summary: "Additional confirmation context is pending.",
      reason: "Needs confirmation.",
    }),
  ],
  avoid_conditions: [
    item({
      id: "avoid-1",
      title: "Avoid condition",
      summary: "No directional signal.",
      reason: "No directional signal.",
    }),
  ],
  outcome_updates: [
    item({
      id: "outcome-1",
      title: "Outcome update",
      summary: "Outcome ready.",
      reason: "Outcome ready.",
    }),
  ],
  pending_actions: [
    item({
      id: "pending-action-1",
      title: "Run deterministic scan",
      summary: "Run deterministic scan.",
      href: "/scanner",
    }),
  ],
  notifications: {
    unread_count: 0,
    acknowledged_count: 1,
    latest: [],
    metadata_json: {},
  },
  journal_prompts: [
    item({
      id: "journal-1",
      title: "Journal prompt",
      summary: "Review setup context.",
      href: "/journal",
    }),
  ],
  quality_warnings: [
    item({
      id: "quality-1",
      title: "Quality warning",
      summary: "Review recommended.",
      href: "/quality",
    }),
  ],
  navigation_hints: [],
  missing_sections: [],
  warnings: [],
};

export const missingSectionsWorkspaceOverview: WorkspaceOverview = {
  ...readyWorkspaceOverview,
  missing_sections: ["notifications", "journal"],
  warnings: ["Optional endpoint unavailable."],
};

export const degradedWorkspaceOverview: WorkspaceOverview = {
  ...readyWorkspaceOverview,
  readiness: {
    status: "degraded",
    label: "Setup incomplete",
    summary: "Review setup context.",
    metadata_json: {},
  },
  data_freshness: {
    status: "stale",
    label: "Data stale",
    summary: "Data stale.",
    metadata_json: {
      freshCount: 0,
      staleOrDegradedCount: 2,
    },
  },
  warnings: ["Data stale."],
};

export const quickActionSuccessResponse: WorkspaceQuickActionResponse = {
  workspace_id: demoWorkspaceId,
  action_type: "run_daily_workflow",
  status: "completed",
  summary: "Deterministic daily workflow completed.",
  created_artifact_ids_json: {
    dailyWorkflowRunId: "44444444-4444-4444-8444-444444444444",
  },
  result_json: {
    status: "completed",
  },
  warnings: [],
  missing_sections: [],
};
