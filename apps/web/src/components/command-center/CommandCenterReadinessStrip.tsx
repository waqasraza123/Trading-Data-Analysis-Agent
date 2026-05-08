import Link from "next/link";
import { overviewHref, overviewStatusTone } from "@/lib/command-center/overviewLabels";
import type { WorkspaceOverview } from "@/lib/command-center/overviewTypes";
import { AnimatedListItem, MOTION_INTERACTIVE_CLASS, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import { CockpitBadge, CockpitMetric } from "./CommandCenterCockpitPrimitives";

export function CommandCenterReadinessStrip({ overview }: { overview: WorkspaceOverview }) {
  const providerIssueCount = readNumber(overview.provider_health.metadata_json, "missingCandleCount");
  const staleCount = readNumber(overview.data_freshness.metadata_json, "staleOrDegradedCount");
  const freshCount = readNumber(overview.data_freshness.metadata_json, "freshCount");
  const staleWorkers = readNumber(overview.workflow.metadata_json, "staleInstanceCount");
  return (
    <section className={`grid gap-3 md:grid-cols-2 xl:grid-cols-5 ${motionRevealPresetClass("scale-subtle")}`}>
      <AnimatedListItem as="article" style={motionRevealDensityStyle(0, "compact")}>
        <Link
          href={overviewHref("/readiness", overview.workspace_id)}
          className={`rounded-2xl border border-slate-200 bg-white/80 p-4 ${motionCardClass} ${MOTION_INTERACTIVE_CLASS}`}
        >
          <p className="text-xs font-semibold uppercase text-slate-500">Readiness</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <CockpitBadge tone={overviewStatusTone(overview.readiness.status)}>{overview.readiness.label}</CockpitBadge>
          </div>
          <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{overview.readiness.summary}</p>
        </Link>
      </AnimatedListItem>
      <AnimatedListItem as="article" style={motionRevealDensityStyle(1, "compact")}>
        <CockpitMetric label="Data fresh" value={freshCount} detail="Fresh contexts" tone="good" />
      </AnimatedListItem>
      <AnimatedListItem as="article" style={motionRevealDensityStyle(2, "compact")}>
        <CockpitMetric label="Data review" value={staleCount} detail="Stale or degraded" tone={staleCount ? "warning" : "neutral"} />
      </AnimatedListItem>
      <AnimatedListItem as="article" style={motionRevealDensityStyle(3, "compact")}>
        <CockpitMetric label="Provider issues" value={providerIssueCount} detail="Missing candles" tone={providerIssueCount ? "warning" : "good"} />
      </AnimatedListItem>
      <AnimatedListItem as="article" style={motionRevealDensityStyle(4, "compact")}>
        <CockpitMetric label="Runtime stale" value={staleWorkers} detail={overview.workflow.label} tone={staleWorkers ? "warning" : "neutral"} />
      </AnimatedListItem>
    </section>
  );
}

function readNumber(metadata: Record<string, unknown>, key: string): number {
  const value = metadata[key];
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}
