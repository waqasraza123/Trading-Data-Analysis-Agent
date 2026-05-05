import type {
  ProductReadinessCheck,
  ProductReadinessCheckStatus,
  ProductReadinessLabel,
  ProductReadinessRun,
} from "./types";

export type ReadinessTone = "neutral" | "good" | "warning" | "danger" | "info";

export function readinessLabelText(label: ProductReadinessLabel | string): string {
  const labels: Record<string, string> = {
    ready: "Ready",
    needs_setup: "Needs setup",
    degraded: "Degraded",
    blocked: "Blocked",
    unknown: "Unknown",
  };
  return labels[label] || label;
}

export function readinessLabelTone(label: ProductReadinessLabel | string): ReadinessTone {
  if (label === "ready") {
    return "good";
  }
  if (label === "needs_setup" || label === "degraded") {
    return "warning";
  }
  if (label === "blocked") {
    return "danger";
  }
  return "neutral";
}

export function checkStatusTone(status: ProductReadinessCheckStatus | string): ReadinessTone {
  if (status === "passed") {
    return "good";
  }
  if (status === "warning" || status === "skipped") {
    return "warning";
  }
  if (status === "failed") {
    return "danger";
  }
  return "neutral";
}

export function readinessScorePercent(run: ProductReadinessRun | null): string {
  if (!run) {
    return "0%";
  }
  return `${Math.round(run.readiness_score * 100)}%`;
}

export function checksByStatus(
  checks: ProductReadinessCheck[],
): Record<ProductReadinessCheckStatus, number> {
  return checks.reduce(
    (counts, check) => ({
      ...counts,
      [check.status]: counts[check.status] + 1,
    }),
    { passed: 0, warning: 0, failed: 0, skipped: 0 },
  );
}

export function remediationHref(check: ProductReadinessCheck, workspaceId?: string | null): string {
  const route = check.related_route || routeForCheckKey(check.key);
  if (!workspaceId) {
    return route;
  }
  const separator = route.includes("?") ? "&" : "?";
  return `${route}${separator}workspaceId=${workspaceId}`;
}

export function remediationLabel(check: ProductReadinessCheck): string {
  const route = check.related_route || routeForCheckKey(check.key);
  const labels: Record<string, string> = {
    "/data/onboarding": "Data onboarding",
    "/scanner": "Scanner",
    "/preferences/strategy": "Preferences",
    "/notifications": "Notifications",
    "/command-center": "Command Center",
    "/journal": "Journal",
    "/health": "API health",
    "/health/db": "Database health",
    "/health/workers": "Worker health",
  };
  return labels[route] || "Open remediation";
}

function routeForCheckKey(key: string): string {
  if (
    key.includes("data") ||
    key.includes("source") ||
    key.includes("symbol") ||
    key.includes("fresh") ||
    key.includes("provider") ||
    key.includes("stale")
  ) {
    return "/data/onboarding";
  }
  if (key.includes("watchlist") || key.includes("scan")) {
    return "/scanner";
  }
  if (key.includes("notification")) {
    return "/notifications";
  }
  if (key.includes("journal")) {
    return "/journal";
  }
  if (key.includes("user")) {
    return "/preferences/strategy";
  }
  return "/command-center";
}
