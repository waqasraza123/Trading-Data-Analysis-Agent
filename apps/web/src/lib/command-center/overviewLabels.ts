import type { CommandCenterTone } from "./types";
import { sanitizeUnsafeCopy } from "@/lib/safety/safeCopy";

export function overviewLabel(value: string | null | undefined, fallback = "Not available"): string {
  if (!value) {
    return fallback;
  }
  return sanitizeUnsafeCopy(value.replace(/[_-]+/g, " "), fallback);
}

export function overviewStatusTone(status: string | null | undefined): CommandCenterTone {
  const normalized = (status || "").toLowerCase();
  if (["ready", "healthy", "fresh", "completed", "passed"].includes(normalized)) {
    return "good";
  }
  if (["blocked", "failing", "failed", "unavailable"].includes(normalized)) {
    return "danger";
  }
  if (["needs_setup", "degraded", "stale", "missing", "pending", "unknown"].includes(normalized)) {
    return "warning";
  }
  return "info";
}

export function overviewHref(href: string | null | undefined, workspaceId: string): string {
  if (!href) {
    return `/command-center?workspaceId=${workspaceId}`;
  }
  if (href.includes("?")) {
    return href;
  }
  if (href.startsWith("/signals/")) {
    return `${href}?workspaceId=${workspaceId}`;
  }
  return href;
}
