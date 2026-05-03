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
    <form className="surface grid gap-3 rounded-lg p-4 md:grid-cols-2 xl:grid-cols-6" action="/notifications">
      {workspaceId && <input type="hidden" name="workspaceId" value={workspaceId} />}
      <label className="grid gap-1 text-sm">
        <span className="text-xs font-semibold uppercase text-slate-500">Inbox</span>
        <select className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]" name="inboxStatus" defaultValue={data.filters.inboxStatus || ""}>
          <option value="">All</option>
          {notificationInboxStatuses.map((status) => (
            <option key={status} value={status}>{notificationInboxStatusLabel(status)}</option>
          ))}
        </select>
      </label>
      <label className="grid gap-1 text-sm">
        <span className="text-xs font-semibold uppercase text-slate-500">Severity</span>
        <select className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]" name="severity" defaultValue={data.filters.severity || ""}>
          <option value="">All</option>
          {notificationSeverities.map((severity) => (
            <option key={severity} value={severity}>{notificationSeverityLabel(severity)}</option>
          ))}
        </select>
      </label>
      <label className="grid gap-1 text-sm">
        <span className="text-xs font-semibold uppercase text-slate-500">Event type</span>
        <select className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]" name="eventType" defaultValue={data.filters.eventType || ""}>
          <option value="">All</option>
          {supportedNotificationEventTypes.map((eventType) => (
            <option key={eventType} value={eventType}>{notificationEventTypeLabel(eventType)}</option>
          ))}
        </select>
      </label>
      <label className="grid gap-1 text-sm">
        <span className="text-xs font-semibold uppercase text-slate-500">Delivery state</span>
        <select className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]" name="status" defaultValue={data.filters.status || ""}>
          <option value="">All</option>
          {notificationEventStatuses.map((status) => (
            <option key={status} value={status}>{notificationStatusLabel(status)}</option>
          ))}
        </select>
      </label>
      <label className="grid gap-1 text-sm">
        <span className="text-xs font-semibold uppercase text-slate-500">Source type</span>
        <input
          className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
          name="sourceType"
          defaultValue={data.filters.sourceType || ""}
          placeholder="signal, outcome, digest"
        />
      </label>
      <div className="flex items-end gap-2">
        <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white" type="submit">
          Apply filters
        </button>
        <a className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold text-[var(--strong)]" href={workspaceId ? `/notifications?workspaceId=${workspaceId}` : "/notifications"}>
          Reset
        </a>
      </div>
    </form>
  );
}
