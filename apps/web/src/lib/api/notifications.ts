import { getPublicEnv } from "@/config/env";
import { apiGet, apiPost } from "./client";
import { listWorkspaces } from "./market";
import type { ApiResult, UUID } from "./types";
import {
  notificationEventStatuses,
  notificationInboxStatuses,
  notificationSeverities,
  supportedNotificationEventTypes,
} from "@/lib/notifications/labels";
import {
  notificationFailure,
  type NotificationDeliveryAttempt,
  type NotificationEvent,
  type NotificationEventStatus,
  type NotificationEventType,
  type NotificationFailure,
  type NotificationFilters,
  type NotificationInboxData,
  type NotificationInboxStatus,
  type NotificationSeverity,
} from "@/lib/notifications/types";

export function listNotificationEvents(params: {
  workspaceId: UUID;
  eventType?: NotificationEventType;
  severity?: NotificationSeverity;
  status?: NotificationEventStatus;
  inboxStatus?: NotificationInboxStatus;
  sourceType?: string;
  limit?: number;
  offset?: number;
}): Promise<ApiResult<NotificationEvent[]>> {
  return apiGet<NotificationEvent[]>("/notification-events", {
    optional: true,
    query: {
      workspace_id: params.workspaceId,
      event_type: params.eventType,
      severity: params.severity,
      status: params.status,
      inbox_status: params.inboxStatus,
      source_type: params.sourceType,
      limit: params.limit || 100,
      offset: params.offset || 0,
    },
  });
}

export function getNotificationEvent(eventId: UUID): Promise<ApiResult<NotificationEvent>> {
  return apiGet<NotificationEvent>(`/notification-events/${eventId}`, { optional: true });
}

export function listNotificationDeliveryAttempts(
  eventId: UUID,
): Promise<ApiResult<NotificationDeliveryAttempt[]>> {
  return apiGet<NotificationDeliveryAttempt[]>(`/notification-events/${eventId}/attempts`, {
    optional: true,
  });
}

export function markNotificationEventRead(eventId: UUID): Promise<ApiResult<NotificationEvent>> {
  return apiPost<NotificationEvent>(`/notification-events/${eventId}/read`, undefined, {
    optional: true,
  });
}

export function acknowledgeNotificationEvent(
  eventId: UUID,
  userId?: UUID,
): Promise<ApiResult<NotificationEvent>> {
  return apiPost<NotificationEvent>(
    `/notification-events/${eventId}/acknowledge`,
    { userId },
    { optional: true },
  );
}

export function archiveNotificationEvent(eventId: UUID): Promise<ApiResult<NotificationEvent>> {
  return apiPost<NotificationEvent>(`/notification-events/${eventId}/archive`, undefined, {
    optional: true,
  });
}

export async function getNotificationInboxData(
  params: Record<string, string | undefined>,
): Promise<NotificationInboxData> {
  const env = getPublicEnv();
  const filters = parseNotificationFilters(params);
  const failures: NotificationFailure[] = [];
  const workspacesResult = await listWorkspaces();
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const workspace = workspaces.find((candidate) => candidate.id === filters.workspaceId) || workspaces[0] || null;

  if (!workspace) {
    return {
      appName: env.appName,
      apiBaseUrl: env.apiBaseUrl,
      requestedWorkspaceId: filters.workspaceId || null,
      workspace: null,
      workspaces,
      filters,
      events: [],
      selectedEvent: null,
      attempts: [],
      unreadCount: 0,
      failures,
      lastLoadedAt: new Date().toISOString(),
    };
  }

  const resolvedFilters: NotificationFilters = { ...filters, workspaceId: workspace.id };
  const [eventsResult, unreadResult] = await Promise.all([
    listNotificationEvents({
      workspaceId: workspace.id,
      eventType: resolvedFilters.eventType,
      severity: resolvedFilters.severity,
      status: resolvedFilters.status,
      inboxStatus: resolvedFilters.inboxStatus,
      sourceType: resolvedFilters.sourceType,
      limit: 200,
    }),
    listNotificationEvents({
      workspaceId: workspace.id,
      inboxStatus: "unread",
      limit: 500,
    }),
  ]);
  const events = readResult("Notification events", eventsResult, [], failures);
  const unreadEvents = readResult("Unread notification events", unreadResult, [], failures);
  const selectedEvent = await resolveSelectedEvent(resolvedFilters.selectedEventId, events, failures);
  const attempts = selectedEvent
    ? readResult(
        "Delivery attempts",
        await listNotificationDeliveryAttempts(selectedEvent.id),
        [],
        failures,
      )
    : [];

  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    requestedWorkspaceId: filters.workspaceId || null,
    workspace,
    workspaces,
    filters: resolvedFilters,
    events,
    selectedEvent,
    attempts,
    unreadCount: unreadEvents.length,
    failures,
    lastLoadedAt: new Date().toISOString(),
  };
}

async function resolveSelectedEvent(
  eventId: UUID | undefined,
  events: NotificationEvent[],
  failures: NotificationFailure[],
): Promise<NotificationEvent | null> {
  if (!eventId) {
    return events.find((event) => event.inbox_status !== "archived") || events[0] || null;
  }
  const existing = events.find((event) => event.id === eventId);
  if (existing) {
    return existing;
  }
  const result = await getNotificationEvent(eventId);
  if (result.ok) {
    return result.data;
  }
  failures.push(notificationFailure("Selected notification event", result.error));
  return events[0] || null;
}

function parseNotificationFilters(params: Record<string, string | undefined>): NotificationFilters {
  return {
    workspaceId: params.workspaceId,
    selectedEventId: params.eventId,
    eventType: parseValue(params.eventType, supportedNotificationEventTypes),
    severity: parseValue(params.severity, notificationSeverities),
    status: parseValue(params.status, notificationEventStatuses),
    inboxStatus: parseValue(params.inboxStatus, notificationInboxStatuses),
    sourceType: normalizeSourceType(params.sourceType),
  };
}

function parseValue<T extends string>(value: string | undefined, allowed: T[]): T | undefined {
  return allowed.find((candidate) => candidate === value);
}

function normalizeSourceType(value: string | undefined): string | undefined {
  const normalized = value?.trim().toLowerCase();
  return normalized || undefined;
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: NotificationFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(notificationFailure(label, result.error));
  return fallback;
}
