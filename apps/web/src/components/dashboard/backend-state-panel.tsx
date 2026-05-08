import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { DashboardData } from "@/lib/api/dashboard";
import { formatDateTime } from "@/lib/formatting/dates";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle } from "@/lib/ui/motion";

export function BackendStatePanel({ data }: { data: DashboardData }) {
  return (
    <Panel title="Backend State" eyebrow="API and worker visibility">
      <div className="grid gap-4 lg:grid-cols-3">
        <AnimatedListItem
          as="section"
          className={`${motionCardClass} muted-surface rounded-lg p-4`}
          preset="scale-subtle"
          style={motionRevealDensityStyle(0, "compact")}
        >
          <p className="text-xs font-semibold uppercase text-slate-500">API health</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge value={data.health?.status || "Unavailable"} tone={toneForQuality(data.health?.status)} />
            <Badge value={data.health?.environment || "Environment unknown"} />
          </div>
          <p className="mt-3 text-sm text-slate-500">{data.apiBaseUrl}</p>
        </AnimatedListItem>
        <AnimatedListItem
          as="section"
          className={`${motionCardClass} muted-surface rounded-lg p-4`}
          preset="scale-subtle"
          style={motionRevealDensityStyle(1, "compact")}
        >
          <p className="text-xs font-semibold uppercase text-slate-500">Worker status</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge value={data.workerStatus?.status || "Unavailable"} tone={toneForQuality(data.workerStatus?.status)} />
            <Badge value={data.workerStatus?.database || "Database unknown"} tone={toneForQuality(data.workerStatus?.database)} />
          </div>
        </AnimatedListItem>
        <AnimatedListItem
          as="section"
          className={`${motionCardClass} muted-surface rounded-lg p-4`}
          preset="scale-subtle"
          style={motionRevealDensityStyle(2, "compact")}
        >
          <p className="text-xs font-semibold uppercase text-slate-500">Last updated</p>
          <p className="mt-3 text-sm font-medium text-[var(--strong)]">{formatDateTime(data.lastUpdatedAt)}</p>
          <p className="mt-2 text-sm text-slate-500">Server-rendered refresh state</p>
        </AnimatedListItem>
      </div>
      {data.failures.length > 0 && (
        <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
          <h3 className="text-sm font-semibold">Failed or missing fetch states</h3>
          <div className="mt-3 grid gap-2">
            {data.failures.slice(0, 8).map((failure, index) => (
              <AnimatedListItem
                as="article"
                key={`${failure.label}:${failure.status}:${failure.message}`}
                className={`${motionCardClass} rounded-lg p-3`}
                preset="scale-subtle"
                style={motionRevealDensityStyle(index, "compact")}
              >
                <span className="font-medium">{failure.label}</span>
                <span className="text-amber-700 dark:text-amber-200">
                  {" "}
                  {failure.missing ? "missing endpoint" : failure.message}
                </span>
              </AnimatedListItem>
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}
