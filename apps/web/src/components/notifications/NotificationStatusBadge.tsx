import {
  notificationInboxStatusLabel,
  notificationSafetyStatusLabel,
  notificationStatusLabel,
} from "@/lib/notifications/labels";
import type {
  NotificationEventStatus,
  NotificationInboxStatus,
  NotificationSafetyStatus,
} from "@/lib/notifications/types";

type StatusBadgeProps = {
  value: NotificationEventStatus | NotificationInboxStatus | NotificationSafetyStatus;
  kind?: "event" | "inbox" | "safety";
};

const toneByValue: Record<string, string> = {
  unread: "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-100",
  read: "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
  acknowledged: "border-teal-200 bg-teal-50 text-teal-800 dark:border-teal-900 dark:bg-teal-950 dark:text-teal-100",
  archived: "border-slate-300 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300",
  delivered: "border-teal-200 bg-teal-50 text-teal-800 dark:border-teal-900 dark:bg-teal-950 dark:text-teal-100",
  partially_delivered: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100",
  held: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100",
  pending: "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-100",
  blocked: "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-100",
  cancelled: "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
  failed: "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-100",
  passed: "border-teal-200 bg-teal-50 text-teal-800 dark:border-teal-900 dark:bg-teal-950 dark:text-teal-100",
  redacted: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100",
  review_recommended: "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-100",
};

export function NotificationStatusBadge({ value, kind = "event" }: StatusBadgeProps) {
  const label =
    kind === "inbox"
      ? notificationInboxStatusLabel(value)
      : kind === "safety"
        ? notificationSafetyStatusLabel(value)
        : notificationStatusLabel(value);
  return (
    <span className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-medium ${toneByValue[value] || toneByValue.read}`}>
      {label}
    </span>
  );
}
