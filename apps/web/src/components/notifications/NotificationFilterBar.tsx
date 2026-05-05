import { Button, ButtonLink } from "@/components/ui/Button";
import {
  ReviewField,
  ReviewFilterShell,
  reviewInputClassName,
} from "@/components/review-surfaces/ReviewSurface";
import {
  notificationEventStatuses,
  notificationEventTypeLabel,
  notificationInboxStatusLabel,
  notificationInboxStatuses,
  notificationSeverities,
  notificationSeverityLabel,
  notificationStatusLabel,
  supportedNotificationEventTypes,
} from "@/lib/notifications/labels";
import type { NotificationInboxData } from "@/lib/notifications/types";

export function NotificationFilterBar({ data }: { data: NotificationInboxData }) {
  const workspaceId = data.workspace?.id || data.requestedWorkspaceId || "";
  return (
    <form action="/notifications">
      {workspaceId && <input type="hidden" name="workspaceId" value={workspaceId} />}
      <ReviewFilterShell
        action={
          <>
            <Button variant="primary" type="submit">Apply filters</Button>
            <ButtonLink href={workspaceId ? `/notifications?workspaceId=${workspaceId}` : "/notifications"}>Reset</ButtonLink>
          </>
        }
      >
        <ReviewField label="Inbox">
          <select className={reviewInputClassName()} name="inboxStatus" defaultValue={data.filters.inboxStatus || ""}>
            <option value="">All</option>
            {notificationInboxStatuses.map((status) => (
              <option key={status} value={status}>{notificationInboxStatusLabel(status)}</option>
            ))}
          </select>
        </ReviewField>
        <ReviewField label="Severity">
          <select className={reviewInputClassName()} name="severity" defaultValue={data.filters.severity || ""}>
            <option value="">All</option>
            {notificationSeverities.map((severity) => (
              <option key={severity} value={severity}>{notificationSeverityLabel(severity)}</option>
            ))}
          </select>
        </ReviewField>
        <ReviewField label="Event type">
          <select className={reviewInputClassName()} name="eventType" defaultValue={data.filters.eventType || ""}>
            <option value="">All</option>
            {supportedNotificationEventTypes.map((eventType) => (
              <option key={eventType} value={eventType}>{notificationEventTypeLabel(eventType)}</option>
            ))}
          </select>
        </ReviewField>
        <ReviewField label="Delivery state">
          <select className={reviewInputClassName()} name="status" defaultValue={data.filters.status || ""}>
            <option value="">All</option>
            {notificationEventStatuses.map((status) => (
              <option key={status} value={status}>{notificationStatusLabel(status)}</option>
            ))}
          </select>
        </ReviewField>
        <ReviewField label="Source type">
          <input
            className={reviewInputClassName()}
            name="sourceType"
            defaultValue={data.filters.sourceType || ""}
            placeholder="signal, outcome, digest"
          />
        </ReviewField>
      </ReviewFilterShell>
    </form>
  );
}
