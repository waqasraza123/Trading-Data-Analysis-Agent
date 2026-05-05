import { CandleChart } from "@/components/charts/CandleChart";
import { ChartEmptyState } from "@/components/charts/ChartEmptyState";
import { ChartErrorState } from "@/components/charts/ChartErrorState";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { chartLabel } from "@/lib/charts/labels";
import type { ChartZone } from "@/lib/charts/types";
import { formatDateTime } from "@/lib/formatting/dates";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";

export function SetupVisualPanel({ model }: { model: SetupDetailViewModel }) {
  const chart = model.setupChart;

  return (
    <Panel title="Visual setup context" eyebrow="Final-candle chart">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {chart.badges.map((badge) => (
              <Badge key={`${badge.label}-${badge.value}`} value={`${badge.label}: ${badge.value}`} tone={badge.tone} />
            ))}
          </div>
          <div className="text-sm text-slate-500">
            Latest final candle: {formatDateTime(chart.latestFinalCandle?.timestamp)}
          </div>
        </div>
        {chart.status === "ready" ? (
          <CandleChart
            slots={chart.slots}
            overlays={chart.overlays}
            latestFinalCandle={chart.latestFinalCandle}
          />
        ) : (
          <ChartEmptyState
            title="Chart context unavailable"
            message="The setup detail is still available, but final candle chart data could not be loaded for this signal window."
          />
        )}
        <ChartErrorState failures={chart.failures.filter((failure) => !failure.missing)} />
        {chart.warnings.length > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
            <p className="font-semibold">Data quality warnings</p>
            <ul className="mt-2 space-y-1">
              {chart.warnings.slice(0, 5).map((warning) => (
                <li key={`${warning.code}-${warning.message}`}>{warning.message}</li>
              ))}
            </ul>
          </div>
        )}
        <ZoneSummary zones={chart.overlays.zones} />
      </div>
    </Panel>
  );
}

function ZoneSummary({ zones }: { zones: ChartZone[] }) {
  const visibleZones = zones.slice(0, 8);
  if (visibleZones.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No observation zones, invalidation context, target context zones, or support/resistance context were returned.
      </p>
    );
  }
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {visibleZones.map((zone) => (
        <div key={zone.id} className="muted-surface rounded-lg p-3">
          <p className="text-xs font-semibold uppercase text-slate-500">{chartLabel(zone.kind)}</p>
          <p className="mt-1 text-sm font-medium text-[var(--strong)]">{zone.label}</p>
          <p className="mt-1 text-xs text-slate-500">{zoneValue(zone)}</p>
        </div>
      ))}
    </div>
  );
}

function zoneValue(zone: ChartZone): string {
  if (zone.lower !== null && zone.upper !== null) {
    return `${zone.lower.toFixed(4)} - ${zone.upper.toFixed(4)}`;
  }
  if (zone.level !== null) {
    return zone.level.toFixed(4);
  }
  return zone.detail || "Level unavailable";
}
