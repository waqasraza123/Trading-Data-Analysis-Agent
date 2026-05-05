import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import type { WorkspaceSetupRun } from "@/lib/setup-wizard/types";

export function SetupSummary({ run }: { run: WorkspaceSetupRun | null }) {
  if (!run) {
    return null;
  }
  const complete = run.status === "completed" || run.status === "completed_with_warnings";
  return (
    <Panel title="Setup summary" eyebrow={run.status.replaceAll("_", " ")}>
      <div className="grid gap-3 md:grid-cols-3">
        <SummaryMetric label="Completed" value={String(run.completed_steps_json.length)} />
        <SummaryMetric label="Skipped" value={String(run.skipped_steps_json.length)} />
        <SummaryMetric label="Failed" value={String(run.failed_steps_json.length)} />
      </div>
      {run.error_message && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800 dark:bg-red-950 dark:text-red-100">
          {run.error_message}
        </p>
      )}
      <div className="mt-5 flex flex-wrap gap-3">
        <Link
          className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white"
          href={run.workspace_id ? `/command-center?workspaceId=${run.workspace_id}` : "/command-center"}
        >
          Command Center
        </Link>
        <Link
          className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold"
          href={run.workspace_id ? `/readiness?workspaceId=${run.workspace_id}` : "/readiness"}
        >
          Readiness
        </Link>
        {complete && (
          <Link
            className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold"
            href={run.workspace_id ? `/scanner?workspaceId=${run.workspace_id}` : "/scanner"}
          >
            Scanner
          </Link>
        )}
      </div>
    </Panel>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="muted-surface rounded-lg p-4">
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}
