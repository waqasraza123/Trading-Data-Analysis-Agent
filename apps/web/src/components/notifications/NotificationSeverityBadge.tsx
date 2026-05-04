import { notificationSeverityLabel } from "@/lib/notifications/labels";
import type { NotificationSeverity } from "@/lib/notifications/types";

type NotificationSeverityBadgeProps = {
  severity: NotificationSeverity;
};

const severityClassName: Record<NotificationSeverity, string> = {
  info: "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-100",
  low: "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
  medium: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100",
  high: "border-orange-200 bg-orange-50 text-orange-800 dark:border-orange-900 dark:bg-orange-950 dark:text-orange-100",
  critical: "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-100",
};

export function NotificationSeverityBadge({ severity }: NotificationSeverityBadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-medium ${severityClassName[severity]}`}>
      {notificationSeverityLabel(severity)}
    </span>
  );
}
