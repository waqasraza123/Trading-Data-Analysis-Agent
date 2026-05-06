import type { OnboardingStatusResponse } from "./types";

export function isCommandCenterReady(status: OnboardingStatusResponse | null): boolean {
  return status?.next_step.key === "open_command_center";
}

export function commandCenterGateMessage(status: OnboardingStatusResponse | null): {
  title: string;
  description: string;
  href: string;
} {
  if (!status) {
    return {
      title: "Product readiness unavailable",
      description: "Open onboarding to review setup context before daily analysis.",
      href: "/onboarding",
    };
  }
  if (!status.workspace.exists) {
    return {
      title: "Workspace setup needed",
      description: "Create or select a workspace before loading command center artifacts.",
      href: "/onboarding",
    };
  }
  if (!status.data_sources.configured || status.data_freshness.label === "no_data") {
    return {
      title: "Data setup needed",
      description: "Configure a data source and verify candles before daily analysis.",
      href: withWorkspace("/data/onboarding", status.workspace.workspace_id),
    };
  }
  if (!status.watchlists.configured || !status.scan_configs.configured) {
    return {
      title: "Create watchlist or scan config",
      description: "Create scanner inputs before running the daily deterministic workflow.",
      href: withWorkspace("/scanner", status.workspace.workspace_id),
    };
  }
  if (status.status.readiness_label !== "ready") {
    return {
      title: "Review product readiness",
      description: status.next_step.description,
      href: withWorkspace(status.next_step.route, status.workspace.workspace_id),
    };
  }
  return {
    title: "Command center ready",
    description: "Workspace setup is ready for deterministic analysis.",
    href: withWorkspace("/command-center", status.workspace.workspace_id),
  };
}

export function withWorkspace(path: string, workspaceId?: string | null): string {
  if (!workspaceId) return path;
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}workspaceId=${workspaceId}`;
}
