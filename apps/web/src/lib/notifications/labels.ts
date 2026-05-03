import { humanizeLabel, shortIdentifier } from "@/lib/formatting/labels";
import type {
  NotificationEvent,
  NotificationEventStatus,
  NotificationEventType,
  NotificationInboxStatus,
  NotificationSafetyStatus,
  NotificationSeverity,
} from "./types";

export const supportedNotificationEventTypes: NotificationEventType[] = [
  "signal.classified",
  "signal.review_recommended",
  "outcome.evaluated",
  "digest.created",
  "data_quality.degraded",
  "market_memory.stale",
  "reasoning.action_due",
  "readiness.blocked",
  "operator_review.opened",
  "scan.completed",
  "provider_health.degraded",
  "gap_recovery.needed",
];

export const notificationSeverities: NotificationSeverity[] = ["info", "low", "medium", "high", "critical"];
export const notificationEventStatuses: NotificationEventStatus[] = [
  "pending",
  "held",
  "delivered",
  "partially_delivered",
  "blocked",
  "cancelled",
  "failed",
];
export const notificationInboxStatuses: NotificationInboxStatus[] = ["unread", "read", "acknowledged", "archived"];

const eventTypeLabels: Record<NotificationEventType, string> = {
  "signal.classified": "Setup context available",
  "signal.review_recommended": "Review needed",
  "outcome.evaluated": "Outcome ready",
  "digest.created": "Digest ready",
  "data_quality.degraded": "Data stale",
  "market_memory.stale": "Data stale",
  "reasoning.action_due": "Review needed",
  "readiness.blocked": "Review needed",
  "operator_review.opened": "Review needed",
  "scan.completed": "Scan completed",
  "provider_health.degraded": "Provider degraded",
  "gap_recovery.needed": "Gap recovery needed",
};

export function notificationEventTypeLabel(value: NotificationEventType | string): string {
  return eventTypeLabels[value as NotificationEventType] || humanizeLabel(value);
}

export function notificationSeverityLabel(value: NotificationSeverity | string): string {
  return humanizeLabel(value);
}

export function notificationStatusLabel(value: NotificationEventStatus | string): string {
  if (value === "held") {
    return "On hold";
  }
  if (value === "partially_delivered") {
    return "Partially stored";
  }
  return humanizeLabel(value);
}

export function notificationInboxStatusLabel(value: NotificationInboxStatus | string): string {
  if (value === "acknowledged") {
    return "Acknowledged";
  }
  return humanizeLabel(value);
}

export function notificationSafetyStatusLabel(value: NotificationSafetyStatus | string): string {
  if (value === "passed") {
    return "Safety passed";
  }
  if (value === "redacted") {
    return "Redacted";
  }
  if (value === "review_recommended") {
    return "Review recommended";
  }
  return humanizeLabel(value);
}

export function notificationSourceLabel(event: NotificationEvent): string {
  return `${humanizeLabel(event.source_type)} ${shortIdentifier(event.source_id)}`;
}

export function notificationSourceHref(event: NotificationEvent, workspaceId?: string | null): string {
  const suffix = workspaceId ? `?workspaceId=${workspaceId}` : "";
  const sourceType = event.source_type.toLowerCase();
  if (sourceType === "signal") {
    return `/signals/${event.source_id}${suffix}`;
  }
  if (sourceType === "journal" || sourceType === "journal_entry") {
    return `/journal?entryId=${event.source_id}${workspaceId ? `&workspaceId=${workspaceId}` : ""}`;
  }
  if (sourceType === "digest" || sourceType === "signal_digest") {
    return `/brief${suffix}`;
  }
  if (sourceType === "outcome" || sourceType === "signal_outcome") {
    return `/review/outcomes${suffix}`;
  }
  if (sourceType === "provider_health" || sourceType === "data_quality" || sourceType === "gap_recovery") {
    return `/data/onboarding${suffix}`;
  }
  if (sourceType === "action_item" || sourceType === "reasoning_action_item" || sourceType === "reasoning_run") {
    return `/command-center${suffix}`;
  }
  if (sourceType === "scan" || sourceType === "scheduled_scan_run") {
    return `/scanner${suffix}`;
  }
  return `/command-center${suffix}`;
}

export function summarizeNotificationPayload(event: NotificationEvent): Array<{ label: string; value: string }> {
  return Object.entries(event.payload_json)
    .filter(([key]) => key !== "deliverySafety" && key !== "delivery_safety")
    .slice(0, 8)
    .map(([key, value]) => ({
      label: humanizeLabel(key),
      value: summarizePayloadValue(value),
    }));
}

export function notificationSafetyWarnings(event: NotificationEvent): string[] {
  const deliverySafety = event.payload_json.deliverySafety || event.payload_json.delivery_safety;
  if (!deliverySafety || typeof deliverySafety !== "object" || Array.isArray(deliverySafety)) {
    return [];
  }
  const warnings = (deliverySafety as Record<string, unknown>).warnings;
  return Array.isArray(warnings) ? warnings.map((warning) => String(warning)).slice(0, 8) : [];
}

function summarizePayloadValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "Not available";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `${value.length} item${value.length === 1 ? "" : "s"}`;
  }
  if (typeof value === "object") {
    return `${Object.keys(value).length} field${Object.keys(value).length === 1 ? "" : "s"}`;
  }
  return String(value);
}
