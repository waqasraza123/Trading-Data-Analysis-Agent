import Link from "next/link";
import { overviewHref, overviewStatusTone } from "@/lib/command-center/overviewLabels";
import type { WorkspaceOverview, WorkspaceOverviewItem } from "@/lib/command-center/overviewTypes";
import { sanitizeUnsafeCopy } from "@/lib/safety/safeCopy";
import { CockpitBadge, CockpitEmptyState, CockpitPanel } from "./CommandCenterCockpitPrimitives";

export function CommandCenterWorkflowStatus({ overview }: { overview: WorkspaceOverview }) {
  return (
    <CockpitPanel title="Workflow Status" eyebrow="Latest persisted state">
      <div className="space-y-3">
        {[overview.daily_brief, overview.workflow].map((status) => (
          <div key={status.label} className="rounded-2xl border border-slate-200 bg-slate-50/75 p-4 dark:border-slate-800 dark:bg-slate-900/45">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="font-semibold text-[var(--strong)]">{sanitizeUnsafeCopy(status.label)}</p>
              <CockpitBadge tone={overviewStatusTone(status.status)}>{sanitizeUnsafeCopy(status.status)}</CockpitBadge>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeUnsafeCopy(status.summary)}</p>
          </div>
        ))}
      </div>
    </CockpitPanel>
  );
}

export function CommandCenterOverviewItemList({
  title,
  eyebrow,
  items,
  empty,
  workspaceId,
}: {
  title: string;
  eyebrow: string;
  items: WorkspaceOverviewItem[];
  empty: string;
  workspaceId?: string;
}) {
  return (
    <CockpitPanel title={title} eyebrow={eyebrow}>
      {items.length === 0 ? (
        <CockpitEmptyState title={empty} message="Stored artifacts do not currently provide items for this section." />
      ) : (
        <div className="space-y-3">
          {items.slice(0, 6).map((item) => (
            <Link key={item.id} href={overviewHref(item.href, workspaceId || "")} className="block rounded-2xl border border-slate-200 bg-white/70 p-4 transition hover:bg-white dark:border-slate-800 dark:bg-slate-950/45">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-[var(--strong)]">{sanitizeUnsafeCopy(item.title)}</p>
                  <p className="mt-1 text-sm text-slate-500">{[item.symbol, item.timeframe].filter(Boolean).join(" ") || "Workspace context"}</p>
                </div>
                {item.bias && <CockpitBadge tone={overviewStatusTone(item.bias)}>{sanitizeUnsafeCopy(item.bias)}</CockpitBadge>}
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeUnsafeCopy(item.reason || item.summary)}</p>
            </Link>
          ))}
        </div>
      )}
    </CockpitPanel>
  );
}
