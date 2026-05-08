import Link from "next/link";
import type { CSSProperties } from "react";
import { formatRelativeTime } from "@/lib/formatting/dates";
import { notificationEventTypeLabel, notificationSourceLabel } from "@/lib/notifications/labels";
import type { NotificationEvent, NotificationFilters } from "@/lib/notifications/types";
import { cn } from "@/lib/ui/cn";
import { NotificationSeverityBadge } from "./NotificationSeverityBadge";
import { NotificationStatusBadge } from "./NotificationStatusBadge";

type NotificationCardProps = {
  event: NotificationEvent;
  selected: boolean;
  filters: NotificationFilters;
  style?: CSSProperties;
  className?: string;
};

export function NotificationCard({ event, selected, filters, style, className }: NotificationCardProps) {
  const href = buildEventHref(event, filters);
  return (
    <Link
      style={style}
      className={cn(
        "block rounded-lg border p-4 transition hover:border-[var(--accent)]",
        selected ? "border-[var(--accent)] bg-[var(--accent-soft)]/40" : "border-[var(--line)] bg-[var(--panel)]",
        className,
      )}
      href={href}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase text-slate-500">{notificationEventTypeLabel(event.event_type)}</p>
          <h3 className="mt-1 line-clamp-2 text-sm font-semibold text-[var(--strong)]">{event.title}</h3>
        </div>
        <NotificationSeverityBadge severity={event.severity} />
      </div>
      <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{event.summary}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <NotificationStatusBadge value={event.inbox_status} kind="inbox" />
        <NotificationStatusBadge value={event.status} />
        <NotificationStatusBadge value={event.safety_status} kind="safety" />
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span>{notificationSourceLabel(event)}</span>
        <span>{formatRelativeTime(event.created_at)}</span>
      </div>
    </Link>
  );
}

function buildEventHref(event: NotificationEvent, filters: NotificationFilters): string {
  const params = new URLSearchParams();
  if (filters.workspaceId) {
    params.set("workspaceId", filters.workspaceId);
  }
  if (filters.inboxStatus) {
    params.set("inboxStatus", filters.inboxStatus);
  }
  if (filters.severity) {
    params.set("severity", filters.severity);
  }
  if (filters.eventType) {
    params.set("eventType", filters.eventType);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.sourceType) {
    params.set("sourceType", filters.sourceType);
  }
  params.set("eventId", event.id);
  return `/notifications?${params.toString()}`;
}
