"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { formatDateTime, formatRelativeTime } from "@/lib/formatting/dates";
import {
  notificationEventTypeLabel,
  notificationSafetyWarnings,
  notificationSourceHref,
  notificationSourceLabel,
  summarizeNotificationPayload,
} from "@/lib/notifications/labels";
import {
  acknowledgeNotificationEvent,
  archiveNotificationEvent,
  markNotificationEventRead,
} from "@/lib/api/notifications";
import type { ApiError } from "@/lib/api/types";
import type { NotificationInboxData } from "@/lib/notifications/types";
import { NotificationEmptyState } from "./NotificationEmptyState";
import { NotificationSeverityBadge } from "./NotificationSeverityBadge";
import { NotificationStatusBadge } from "./NotificationStatusBadge";

type NotificationDetailPanelProps = {
  data: NotificationInboxData;
};

export function NotificationDetailPanel({ data }: NotificationDetailPanelProps) {
  const router = useRouter();
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const event = data.selectedEvent;

  if (!event) {
    return (
      <NotificationEmptyState
        title="Select a notification"
        message="Choose an event to review payload summary, source context, safety status, and delivery attempts."
      />
    );
  }

  const payloadSummary = summarizeNotificationPayload(event);
  const warnings = notificationSafetyWarnings(event);
  const sourceHref = notificationSourceHref(event, data.workspace?.id);
  const eventId = event.id;

  async function runAction(action: "read" | "acknowledge" | "archive") {
    setPendingAction(action);
    setError(null);
    const result =
      action === "read"
        ? await markNotificationEventRead(eventId)
        : action === "acknowledge"
          ? await acknowledgeNotificationEvent(eventId)
          : await archiveNotificationEvent(eventId);
    setPendingAction(null);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    router.refresh();
  }

  return (
    <section className="surface rounded-lg p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">{notificationEventTypeLabel(event.event_type)}</p>
          <h2 className="mt-1 text-2xl font-semibold text-[var(--strong)]">{event.title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">{event.summary}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <NotificationSeverityBadge severity={event.severity} />
          <NotificationStatusBadge value={event.inbox_status} kind="inbox" />
          <NotificationStatusBadge value={event.safety_status} kind="safety" />
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-md border border-[var(--danger)] bg-[var(--danger-soft)] px-3 py-2 text-sm text-[var(--danger)]">
          {error.message}
        </div>
      )}

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <DetailItem label="Source" value={notificationSourceLabel(event)} href={sourceHref} />
        <DetailItem label="Created" value={formatDateTime(event.created_at)} detail={formatRelativeTime(event.created_at)} />
        <DetailItem label="Delivery state" value={event.status} />
        <DetailItem label="External delivery" value="Not triggered" />
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {event.inbox_status === "unread" && (
          <button
            className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            type="button"
            disabled={pendingAction !== null}
            onClick={() => runAction("read")}
          >
            {pendingAction === "read" ? "Saving" : "Mark read"}
          </button>
        )}
        {event.inbox_status !== "acknowledged" && event.inbox_status !== "archived" && (
          <button
            className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold text-[var(--strong)] disabled:cursor-not-allowed disabled:opacity-60"
            type="button"
            disabled={pendingAction !== null}
            onClick={() => runAction("acknowledge")}
          >
            {pendingAction === "acknowledge" ? "Saving" : "Acknowledge"}
          </button>
        )}
        {event.inbox_status !== "archived" && (
          <button
            className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold text-[var(--strong)] disabled:cursor-not-allowed disabled:opacity-60"
            type="button"
            disabled={pendingAction !== null}
            onClick={() => runAction("archive")}
          >
            {pendingAction === "archive" ? "Saving" : "Archive"}
          </button>
        )}
      </div>

      <div className="mt-6 grid gap-5 xl:grid-cols-2">
        <section>
          <h3 className="text-sm font-semibold text-[var(--strong)]">Safe payload summary</h3>
          {payloadSummary.length === 0 ? (
            <p className="mt-3 rounded-md bg-[var(--panel-muted)] px-3 py-2 text-sm text-slate-500">No displayable payload fields.</p>
          ) : (
            <div className="mt-3 grid gap-2">
              {payloadSummary.map((item) => (
                <div key={item.label} className="rounded-md border border-[var(--line)] bg-[var(--panel-muted)] px-3 py-2">
                  <p className="text-xs font-semibold uppercase text-slate-500">{item.label}</p>
                  <p className="mt-1 break-words text-sm text-[var(--strong)]">{item.value}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <h3 className="text-sm font-semibold text-[var(--strong)]">Safety status</h3>
          <div className="mt-3 rounded-md border border-[var(--line)] bg-[var(--panel-muted)] p-3">
            <NotificationStatusBadge value={event.safety_status} kind="safety" />
            {warnings.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">No redaction warnings were recorded.</p>
            ) : (
              <div className="mt-3 grid gap-2">
                {warnings.map((warning) => (
                  <p key={warning} className="rounded-md bg-[var(--warn-soft)] px-3 py-2 text-sm text-[var(--warn)]">{warning}</p>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="mt-6">
        <h3 className="text-sm font-semibold text-[var(--strong)]">Delivery attempts</h3>
        {data.attempts.length === 0 ? (
          <p className="mt-3 rounded-md bg-[var(--panel-muted)] px-3 py-2 text-sm text-slate-500">No delivery attempts were recorded.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-y-2 text-left text-sm">
              <thead className="text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Attempted</th>
                  <th className="px-3 py-2">Response</th>
                  <th className="px-3 py-2">Message</th>
                </tr>
              </thead>
              <tbody>
                {data.attempts.map((attempt) => (
                  <tr key={attempt.id} className="bg-[var(--panel-muted)]">
                    <td className="rounded-l-md px-3 py-2">{attempt.status}</td>
                    <td className="px-3 py-2">{formatDateTime(attempt.attempted_at)}</td>
                    <td className="px-3 py-2">{attempt.response_status_code ?? "Not available"}</td>
                    <td className="rounded-r-md px-3 py-2">{attempt.error_message || attempt.response_body_excerpt || "Not available"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}

function DetailItem({
  label,
  value,
  detail,
  href,
}: {
  label: string;
  value: string;
  detail?: string;
  href?: string;
}) {
  const content = (
    <>
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 break-words text-sm font-medium text-[var(--strong)]">{value}</p>
      {detail && <p className="mt-1 text-xs text-slate-500">{detail}</p>}
    </>
  );
  if (!href) {
    return <div className="rounded-md border border-[var(--line)] bg-[var(--panel-muted)] p-3">{content}</div>;
  }
  return (
    <Link className="rounded-md border border-[var(--line)] bg-[var(--panel-muted)] p-3 hover:border-[var(--accent)]" href={href}>
      {content}
    </Link>
  );
}
