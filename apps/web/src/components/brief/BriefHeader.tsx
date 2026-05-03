import Link from "next/link";
import { Badge } from "@/components/status/badge";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import type { WorkspaceBrief } from "@/lib/brief/types";
import { formatDateTime } from "@/lib/formatting/dates";

export function BriefHeader({ brief }: { brief: WorkspaceBrief }) {
  return (
    <section className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-slate-500">Workspace brief</p>
        <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">What to review now</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
          Deterministic morning and intraday context across symbol state, setup context, outcomes, backend actions, and review queues.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Badge value={brief.workspace?.name || "No workspace"} tone="info" />
          <Badge value={`Generated ${formatDateTime(brief.generatedAt)}`} />
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Link
          className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium hover:bg-white dark:hover:bg-slate-900"
          href="/dashboard"
        >
          Dashboard
        </Link>
        {brief.workspace && (
          <Link
            className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium hover:bg-white dark:hover:bg-slate-900"
            href={`/dashboard?workspaceId=${brief.workspace.id}`}
          >
            Workspace dashboard
          </Link>
        )}
        <WorkflowLinks workspaceId={brief.workspace?.id} targets={["triage", "scanner", "dataOnboarding"]} />
      </div>
    </section>
  );
}
