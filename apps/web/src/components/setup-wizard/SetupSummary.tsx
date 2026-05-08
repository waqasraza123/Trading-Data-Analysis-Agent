import Link from "next/link";
import { cn } from "@/lib/ui/cn";
import { Panel } from "@/components/layout/panel";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import type { WorkspaceSetupRun } from "@/lib/setup-wizard/types";

export function SetupSummary({ run }: { run: WorkspaceSetupRun | null }) {
  if (!run) {
    return null;
  }
  const complete = run.status === "completed" || run.status === "completed_with_warnings";
  return (
    <Panel
      title="Setup summary"
      eyebrow={run.status.replaceAll("_", " ")}
      className={cn("rounded-lg", motionCardClass, motionRevealPresetClass("scale-subtle"))}
    >
      <div className="grid gap-3 md:grid-cols-3">
        <SummaryMetric label="Completed" value={String(run.completed_steps_json.length)} index={0} />
        <SummaryMetric label="Skipped" value={String(run.skipped_steps_json.length)} index={1} />
        <SummaryMetric label="Failed" value={String(run.failed_steps_json.length)} index={2} />
      </div>
      {run.error_message && (
        <AnimatedListItem
          as="p"
          className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800 dark:bg-red-950 dark:text-red-100"
          style={motionRevealDensityStyle(3, "compact")}
        >
          {run.error_message}
        </AnimatedListItem>
      )}
      <div className="mt-5 flex flex-wrap gap-3">
        <SummaryAction
          href={run.workspace_id ? `/command-center?workspaceId=${run.workspace_id}` : "/command-center"}
          index={0}
          className="rounded-md bg-[var(--accent)] text-white"
        >
          Command Center
        </SummaryAction>
        <SummaryAction
          href={run.workspace_id ? `/readiness?workspaceId=${run.workspace_id}` : "/readiness"}
          index={1}
          className="rounded-md border border-[var(--line)]"
        >
          Readiness
        </SummaryAction>
        {complete && (
          <SummaryAction
            href={run.workspace_id ? `/scanner?workspaceId=${run.workspace_id}` : "/scanner"}
            index={2}
            className="rounded-md border border-[var(--line)]"
          >
            Scanner
          </SummaryAction>
        )}
      </div>
    </Panel>
  );
}

function SummaryMetric({ label, value, index }: { label: string; value: string; index: number }) {
  return (
    <AnimatedListItem
      as="article"
      className={cn("muted-surface rounded-lg p-4", motionCardClass, motionRevealPresetClass("scale-subtle"))}
      style={motionRevealDensityStyle(index, "compact")}
    >
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-[var(--strong)]">{value}</p>
    </AnimatedListItem>
  );
}

function SummaryAction({
  children,
  className,
  href,
  index,
}: {
  children: string;
  className: string;
  href: string;
  index: number;
}) {
  return (
    <AnimatedListItem
      as="span"
      style={motionRevealDensityStyle(index, "compact")}
    >
      <Link
        href={href}
        className={cn(
          "px-4 py-2 text-sm font-semibold",
          className,
          motionCardClass,
          motionRevealPresetClass("scale-subtle"),
        )}
      >
        {children}
      </Link>
    </AnimatedListItem>
  );
}
