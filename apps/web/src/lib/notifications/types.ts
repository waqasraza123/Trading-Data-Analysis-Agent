import type { ApiError, JsonRecord, UUID, Workspace } from "@/lib/api/types";

export type NotificationEventType =
  | "signal.classified"
  | "signal.review_recommended"
  | "outcome.evaluated"
  | "digest.created"
  | "data_quality.degraded"
  | "market_memory.stale"
  | "reasoning.action_due"
  | "readiness.blocked"
  | "operator_review.opened"
  | "scan.completed"
  | "provider_health.degraded"
  | "gap_recovery.needed";

export type NotificationSeverity = "info" | "low" | "medium" | "high" | "critical";
export type NotificationEventStatus =
  | "pending"
  | "held"
  | "delivered"
  | "partially_delivered"
  | "blocked"
  | "cancelled"
  | "failed";
export type NotificationInboxStatus = "unread" | "read" | "acknowledged" | "archived";
export type NotificationSafetyStatus = "passed" | "blocked" | "redacted" | "review_recommended";
export type NotificationDeliveryAttemptStatus = "pending" | "delivered" | "skipped" | "failed" | "blocked";

export type NotificationEvent = {
  id: UUID;
  workspace_id: UUID;
  event_type: NotificationEventType;
  source_type: string;
  source_id: UUID;
  severity: NotificationSeverity;
  status: NotificationEventStatus;
  inbox_status: NotificationInboxStatus;
  title: string;
  summary: string;
  payload_json: JsonRecord;
  safety_status: NotificationSafetyStatus;
  dedupe_key: string;
  read_at: string | null;
  acknowledged_at: string | null;
  acknowledged_by_user_id: UUID | null;
  created_at: string;
  updated_at: string;
};

export type NotificationDeliveryAttempt = {
  id: UUID;
  workspace_id: UUID;
  notification_event_id: UUID;
  channel_id: UUID;
  status: NotificationDeliveryAttemptStatus;
  attempted_at: string;
  response_status_code: number | null;
  response_body_excerpt: string | null;
  error_message: string | null;
  metadata_json: JsonRecord;
  created_at: string;
};

export type NotificationFilters = {
  workspaceId?: UUID;
  eventType?: NotificationEventType;
  severity?: NotificationSeverity;
  status?: NotificationEventStatus;
  inboxStatus?: NotificationInboxStatus;
  sourceType?: string;
  selectedEventId?: UUID;
};

export type NotificationFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type NotificationInboxData = {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: UUID | null;
  workspace: Workspace | null;
  workspaces: Workspace[];
  filters: NotificationFilters;
  events: NotificationEvent[];
  selectedEvent: NotificationEvent | null;
  attempts: NotificationDeliveryAttempt[];
  unreadCount: number;
  failures: NotificationFailure[];
  lastLoadedAt: string;
};

export function notificationFailure(label: string, error: ApiError): NotificationFailure {
  return {
    label,
    status: error.status,
    message: error.message,
    missing: error.missing,
  };
}
