import { WorkflowLinks } from "@/components/layout/workflow-links";
import type { NotificationInboxData } from "@/lib/notifications/types";

export function NotificationInboxHeader({ data }: { data: NotificationInboxData }) {
  return (
    <section className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-slate-500">Intelligence notification inbox</p>
        <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">Notifications</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
          Review backend-safe intelligence events, source context, delivery attempts, and redaction status inside the product.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-sm text-slate-500">
          <span className="font-medium text-[var(--strong)]">{data.unreadCount}</span> unread
        </div>
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-sm text-slate-500">
          Workspace {data.workspace?.name || "not selected"}
        </div>
        <WorkflowLinks workspaceId={data.workspace?.id} targets={["commandCenter", "brief", "triage", "scanner", "dataOnboarding", "review", "journal"]} />
      </div>
    </section>
  );
}
