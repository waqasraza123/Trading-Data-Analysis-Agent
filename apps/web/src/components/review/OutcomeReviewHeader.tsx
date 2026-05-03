import { WorkflowLinks } from "@/components/layout/workflow-links";
import type { OutcomeReviewData } from "@/lib/review/types";

export function OutcomeReviewHeader({ data }: { data: OutcomeReviewData }) {
  return (
    <section className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-slate-500">Outcome and journal review</p>
        <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">Daily learning loop</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
          Review recently observed signal outcomes, connect notes, and inspect reliability diagnostics without broker execution or advice language.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-sm text-slate-500">
          Workspace {data.workspace?.name || "not selected"}
        </div>
        <WorkflowLinks workspaceId={data.workspace?.id} targets={["commandCenter", "journal", "brief", "triage", "preferences"]} />
      </div>
    </section>
  );
}
