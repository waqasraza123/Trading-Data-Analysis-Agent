import { EmptyState } from "@/components/empty-states/empty-state";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { triageColumns } from "@/lib/triage/labels";
import type { TriageBoardData } from "@/lib/triage/types";
import { SignalTriageColumn } from "./SignalTriageColumn";
import { TriageEmptyState } from "./TriageEmptyState";
import { TriageErrorState } from "./TriageErrorState";
import { TriageFilters } from "./TriageFilters";
import { TriageSummary } from "./TriageSummary";

export function SignalTriageBoard({ data }: { data: TriageBoardData }) {
  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">Deterministic signal review</p>
          <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">Signal triage board</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Prioritize stored deterministic signals by context quality, confirmation needs, conflicts, data freshness, and review state.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-sm text-slate-500">
            Workspace {data.workspace?.name || "not selected"}
          </div>
          <WorkflowLinks workspaceId={data.workspace?.id} targets={["brief", "scanner", "dataOnboarding"]} />
        </div>
      </section>
      {!data.workspace ? (
        <EmptyState
          title="No workspace available"
          message="Seed or create a workspace in the API before workspace-scoped triage can load."
        />
      ) : (
        <>
          <TriageSummary data={data} />
          <TriageFilters data={data} />
          <TriageErrorState failures={data.failures} />
          {data.candidates.length === 0 ? (
            <TriageEmptyState />
          ) : (
            <div className="grid gap-4 xl:grid-cols-3 2xl:grid-cols-6">
              {triageColumns.map((column) => (
                <SignalTriageColumn
                  key={column.key}
                  column={column}
                  candidates={data.candidates.filter((candidate) => candidate.classification.column === column.key)}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
