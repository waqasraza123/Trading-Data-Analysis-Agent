import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { formatRelativeTime } from "@/lib/formatting/dates";
import { humanizeLabel } from "@/lib/formatting/labels";
import type { CommandCenterData, CommandCenterTone } from "@/lib/command-center/types";
import type { RuntimeHealthWorkerSummary } from "@/lib/api/runtimeSupervisor";

export function CommandCenterRuntimeWorkers({ data }: { data: CommandCenterData }) {
  const health = data.runtimeSupervisorHealth;
  const workers = health?.workers.slice(0, 6) || [];
  return (
    <Panel title="Worker health" eyebrow="Runtime supervisor">
      {!health || workers.length === 0 ? (
        <p className="text-sm text-slate-500">{data.sectionStatuses.runtimeWorkers.message}</p>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2 text-sm">
            <RuntimeMetric label="Running" value={health.running_instance_count} />
            <RuntimeMetric label="Stale" value={health.stale_instance_count} />
            <RuntimeMetric label="Pending" value={health.pending_run_request_count} />
          </div>
          <div className="space-y-2">
            {workers.map((worker) => (
              <WorkerRow key={worker.key} worker={worker} />
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}

function RuntimeMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="muted-surface rounded-lg p-3">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}

function WorkerRow({ worker }: { worker: RuntimeHealthWorkerSummary }) {
  return (
    <div className="rounded-lg border border-[var(--line)] p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-[var(--strong)]">{worker.name}</p>
          <p className="mt-1 text-xs text-slate-500">{humanizeLabel(worker.worker_type)}</p>
        </div>
        <Badge value={worker.definition_status} tone={workerTone(worker)} />
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
        {worker.running_instances} running, {worker.stale_instances} stale. Last check-in{" "}
        {formatRelativeTime(worker.last_heartbeat_at)}.
      </p>
      {(worker.pending_run_requests > 0 || worker.failed_run_requests > 0) && (
        <p className="mt-1 text-xs text-slate-500">
          {worker.pending_run_requests} pending requests, {worker.failed_run_requests} failed requests.
        </p>
      )}
    </div>
  );
}

function workerTone(worker: RuntimeHealthWorkerSummary): CommandCenterTone {
  if (worker.definition_status === "unavailable" || worker.failed_run_requests > 0) {
    return "danger";
  }
  if (worker.stale_instances > 0 || worker.pending_run_requests > 0) {
    return "warning";
  }
  if (worker.definition_status === "available" && worker.running_instances > 0) {
    return "good";
  }
  if (worker.definition_status === "disabled") {
    return "neutral";
  }
  return "info";
}
