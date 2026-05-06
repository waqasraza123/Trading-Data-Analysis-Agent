import type { OnboardingStatusResponse } from "../../../src/lib/onboarding/types";
import { demoUserId, demoWorkspaceId } from "./workspaceFixtures";

const baseSteps: OnboardingStatusResponse["steps"] = [
  {
    key: "workspace",
    title: "Workspace",
    description: "Create or select a workspace for deterministic analysis.",
    state: "complete",
    route: "/setup",
    action_type: null,
    metadata: {},
  },
  {
    key: "symbols",
    title: "Symbols",
    description: "Seed symbols for analysis context.",
    state: "complete",
    route: "/setup",
    action_type: null,
    metadata: {},
  },
  {
    key: "data_sources",
    title: "Data sources",
    description: "Configure a data source before freshness checks.",
    state: "complete",
    route: "/data/onboarding",
    action_type: null,
    metadata: {},
  },
  {
    key: "watchlist",
    title: "Watchlist",
    description: "Create a watchlist for deterministic scans.",
    state: "complete",
    route: "/scanner",
    action_type: null,
    metadata: {},
  },
  {
    key: "scan_config",
    title: "Scan config",
    description: "Create a scan config for the daily workflow.",
    state: "complete",
    route: "/scanner",
    action_type: null,
    metadata: {},
  },
];

export const missingWorkspaceOnboardingStatus: OnboardingStatusResponse = {
  status: {
    readiness_label: "needs_setup",
    readiness_score: 10,
    summary: "Setup incomplete.",
  },
  workspace: {
    exists: false,
    workspace_id: null,
    name: null,
  },
  user: {
    exists: false,
    user_id: null,
    role: null,
  },
  symbols: {
    configured: false,
    count: 0,
    missing: true,
  },
  data_sources: {
    configured: false,
    count: 0,
    missing: true,
    provider_ready: false,
  },
  data_freshness: {
    label: "unknown",
    summary: "Freshness context unavailable.",
  },
  watchlists: {
    configured: false,
    count: 0,
    missing: true,
  },
  scan_configs: {
    configured: false,
    count: 0,
    missing: true,
  },
  daily_workflow: {
    available: true,
    last_run_status: null,
  },
  demo_mode: {
    available: true,
    enabled: true,
  },
  next_step: {
    key: "create_workspace",
    title: "Create workspace",
    description: "Create a workspace before daily analysis can load.",
    route: "/setup",
    action_type: "create_workspace",
  },
  steps: [
    {
      ...baseSteps[0],
      state: "incomplete",
      action_type: "create_workspace",
    },
    {
      ...baseSteps[1],
      state: "blocked",
      action_type: "seed_symbols",
    },
    {
      ...baseSteps[2],
      state: "blocked",
      action_type: "seed_default_data_sources",
    },
    {
      ...baseSteps[3],
      state: "blocked",
      action_type: "create_basic_watchlist",
    },
    {
      ...baseSteps[4],
      state: "blocked",
      action_type: "create_basic_scan_config",
    },
  ],
  warnings: [],
  missing_sections: ["workspace", "symbols", "data_sources", "watchlist", "scan_config"],
};

export const partialOnboardingStatus: OnboardingStatusResponse = {
  ...missingWorkspaceOnboardingStatus,
  status: {
    readiness_label: "needs_setup",
    readiness_score: 48,
    summary: "Setup incomplete.",
  },
  workspace: {
    exists: true,
    workspace_id: demoWorkspaceId,
    name: "Demo Analysis Workspace",
  },
  user: {
    exists: true,
    user_id: demoUserId,
    role: "analyst",
  },
  symbols: {
    configured: true,
    count: 3,
    missing: false,
  },
  data_sources: {
    configured: false,
    count: 0,
    missing: true,
    provider_ready: false,
  },
  data_freshness: {
    label: "no_data",
    summary: "No final candles are available.",
  },
  watchlists: {
    configured: false,
    count: 0,
    missing: true,
  },
  scan_configs: {
    configured: false,
    count: 0,
    missing: true,
  },
  next_step: {
    key: "configure_data_source",
    title: "Configure data source",
    description: "Review data onboarding before scanner setup.",
    route: "/data/onboarding",
    action_type: "seed_default_data_sources",
  },
  steps: [
    baseSteps[0],
    baseSteps[1],
    {
      ...baseSteps[2],
      state: "incomplete",
      action_type: "seed_default_data_sources",
    },
    {
      ...baseSteps[3],
      state: "incomplete",
      action_type: "create_basic_watchlist",
    },
    {
      ...baseSteps[4],
      state: "incomplete",
      action_type: "create_basic_scan_config",
    },
  ],
  missing_sections: ["data_sources", "watchlist", "scan_config"],
};

export const readyOnboardingStatus: OnboardingStatusResponse = {
  ...partialOnboardingStatus,
  status: {
    readiness_label: "ready",
    readiness_score: 96,
    summary: "Command center ready.",
  },
  data_sources: {
    configured: true,
    count: 1,
    missing: false,
    provider_ready: true,
  },
  data_freshness: {
    label: "fresh",
    summary: "Data fresh.",
  },
  watchlists: {
    configured: true,
    count: 1,
    missing: false,
  },
  scan_configs: {
    configured: true,
    count: 1,
    missing: false,
  },
  next_step: {
    key: "open_command_center",
    title: "Open command center",
    description: "Workspace is ready for deterministic analysis.",
    route: "/command-center",
    action_type: null,
  },
  steps: baseSteps,
  warnings: [],
  missing_sections: [],
};

export const warningOnboardingStatus: OnboardingStatusResponse = {
  ...readyOnboardingStatus,
  status: {
    readiness_label: "degraded",
    readiness_score: 78,
    summary: "Readiness degraded.",
  },
  warnings: ["Data stale."],
  missing_sections: ["data_freshness"],
};
