import { Panel } from "@/components/layout/panel";
import { WorkerStatusBadge } from "@/components/status/WorkerStatusBadge";
import { Metric } from "@/components/ui/Metric";
import { formatRelativeTime } from "@/lib/formatting/dates";
import { humanizeLabel } from "@/lib/formatting/labels";
import type { CommandCenterData } from "@/lib/command-center/types";
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
  return <Metric label={label} value={value} />;
}

function WorkerRow({ worker }: { worker: RuntimeHealthWorkerSummary }) {
  return (
    <div className="rounded-lg border border-[var(--line)] p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-[var(--strong)]">{worker.name}</p>
          <p className="mt-1 text-xs text-slate-500">{humanizeLabel(worker.worker_type)}</p>
        </div>
        <WorkerStatusBadge value={worker.definition_status} />
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
