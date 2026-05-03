"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { runDailyWorkflow } from "@/lib/api/dailyWorkflows";
import { formatDateTime } from "@/lib/formatting/dates";
import { shortIdentifier } from "@/lib/formatting/labels";
import { safeWorkflowText, workflowStatusTone } from "@/lib/daily-workflows/labels";
import type { DailyWorkflowRun, DailyWorkflowStep } from "@/lib/daily-workflows/types";
import type { UUID } from "@/lib/api/types";

type DailyWorkflowPanelProps = {
  workspaceId: UUID | null;
  watchlistId: UUID | null;
  preferenceProfileId?: UUID | null;
  runs: DailyWorkflowRun[];
  selectedRun: DailyWorkflowRun | null;
  selectedSteps: DailyWorkflowStep[];
  basePath: "/command-center" | "/scanner";
};

export function DailyWorkflowPanel({
  workspaceId,
  watchlistId,
  preferenceProfileId = null,
  runs,
  selectedRun,
  selectedSteps,
  basePath,
}: DailyWorkflowPanelProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const run = selectedRun || runs[0] || null;
  const steps = selectedSteps.length > 0 ? selectedSteps : stepSummariesFromRun(run);
  const scanRunIds = readStringArray(run?.result_json.scanRunIds);
  const signalIds = readStringArray(run?.result_json.signalIds);
  const digestRunIds = readStringArray(run?.result_json.signalDigestRunIds);

  async function runWorkflow() {
    if (!workspaceId) {
      setMessage("Workspace is required.");
      return;
    }
    setPending(true);
    setMessage(null);
    const result = await runDailyWorkflow({
      workspace_id: workspaceId,
      workflow_type: watchlistId ? "watchlist_scan" : "daily_scan",
      watchlist_id: watchlistId || undefined,
      preference_profile_id: preferenceProfileId || null,
      options: {
        prepare_gap_recovery: true,
        allow_provider_polling: false,
        run_scan: true,
        generate_setup_context: true,
        score_priorities: true,
        generate_digest: true,
        generate_brief: true,
      },
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    router.push(workflowHref(searchParams.toString(), basePath, workspaceId, result.data));
    router.refresh();
  }

  return (
    <Panel
      title="Daily workflow"
      eyebrow="One-click deterministic scan"
      action={
        <button
          className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={pending || !workspaceId}
          type="button"
          onClick={runWorkflow}
        >
          {pending ? "Running daily scan" : "Run daily scan"}
        </button>
      }
    >
      {message && <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">{safeWorkflowText(message)}</p>}
      {!run ? (
        <div className="muted-surface rounded-lg p-5 text-sm leading-6 text-slate-500">
          Run the daily scan to refresh data status, prepare recovery plans, run deterministic scans, score review priority, and generate digest context.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="muted-surface rounded-lg p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold text-[var(--strong)]">Workflow {run.id.slice(0, 8)}</h3>
                <p className="mt-1 text-sm text-slate-500">Started {formatDateTime(run.started_at)} · Completed {formatDateTime(run.completed_at)}</p>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{safeWorkflowText(run.summary)}</p>
              </div>
              <Badge value={run.status} tone={workflowStatusTone(run.status)} />
            </div>
            {run.error_message && <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-100">{safeWorkflowText(run.error_message)}</p>}
          </div>
          <div className="grid gap-3 lg:grid-cols-4">
            <WorkflowMetric label="Scan runs" value={scanRunIds.length} />
            <WorkflowMetric label="Signals" value={signalIds.length} />
            <WorkflowMetric label="Digests" value={digestRunIds.length} />
            <WorkflowMetric label="Steps" value={steps.length} />
          </div>
          <div className="grid gap-3">
            {steps.map((step) => (
              <div key={step.id} className="muted-surface flex flex-wrap items-center justify-between gap-3 rounded-lg p-4">
                <div>
                  <p className="text-sm font-semibold text-[var(--strong)]">{safeWorkflowText(step.step_key)}</p>
                  <p className="mt-1 text-xs text-slate-500">{safeWorkflowText(step.skipped_reason || step.error_message, "Step output recorded")}</p>
                </div>
                <Badge value={step.status} tone={workflowStatusTone(step.status)} />
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-2 text-sm">
            <Link className="rounded-md border border-[var(--line)] px-3 py-2 font-medium text-[var(--info)] hover:bg-slate-100 dark:hover:bg-slate-800" href={`/brief?workspaceId=${run.workspace_id}`}>
              Open generated brief
            </Link>
            {scanRunIds.slice(0, 3).map((scanRunId) => (
              <Link key={scanRunId} className="rounded-md border border-[var(--line)] px-3 py-2 font-medium text-[var(--info)] hover:bg-slate-100 dark:hover:bg-slate-800" href={`/scanner?workspaceId=${run.workspace_id}&runId=${scanRunId}&workflowRunId=${run.id}`}>
                Scan run {shortIdentifier(scanRunId)}
              </Link>
            ))}
            {signalIds.slice(0, 5).map((signalId) => (
              <Link key={signalId} className="rounded-md border border-[var(--line)] px-3 py-2 font-medium text-[var(--info)] hover:bg-slate-100 dark:hover:bg-slate-800" href={`/signals/${signalId}`}>
                Signal {shortIdentifier(signalId)}
              </Link>
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}

function WorkflowMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="muted-surface rounded-lg p-4">
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}

function stepSummariesFromRun(run: DailyWorkflowRun | null): DailyWorkflowStep[] {
  if (!run) {
    return [];
  }
  return run.steps_json.map((step, index) => ({
    id: String(step.id || `${run.id}-${index}`),
    workspace_id: run.workspace_id,
    workflow_run_id: run.id,
    step_key: String(step.stepKey || step.step_key || "workflow_step"),
    status: String(step.status || "pending") as DailyWorkflowStep["status"],
    started_at: typeof step.startedAt === "string" ? step.startedAt : null,
    completed_at: typeof step.completedAt === "string" ? step.completedAt : null,
    input_json: {},
    output_json: null,
    skipped_reason: typeof step.skippedReason === "string" ? step.skippedReason : null,
    error_message: typeof step.errorMessage === "string" ? step.errorMessage : null,
    created_at: run.created_at,
    updated_at: run.updated_at,
  }));
}

function workflowHref(searchParams: string, basePath: string, workspaceId: UUID, run: DailyWorkflowRun): string {
  const params = new URLSearchParams(searchParams);
  params.set("workspaceId", workspaceId);
  params.set("workflowRunId", run.id);
  const scanRunId = readStringArray(run.result_json.scanRunIds)[0];
  if (basePath === "/scanner" && scanRunId) {
    params.set("runId", scanRunId);
  }
  return `${basePath}?${params.toString()}`;
}

function readStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string");
}
