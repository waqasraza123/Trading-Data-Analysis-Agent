import { Badge } from "@/components/status/badge";
import { cn } from "@/lib/ui/cn";
import { motionCardClass, motionRevealPresetClass } from "@/lib/ui/motion";
import { formatDateTime } from "@/lib/formatting/dates";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function EquityResearchHeader({ data }: { data: EquityResearchData }) {
  return (
    <section
      className={cn(
        "surface rounded-lg p-6",
        motionCardClass,
        motionRevealPresetClass("scale-subtle"),
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Equity research
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-[var(--strong)]">
            Swing setup candidate review
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Manage stock universes, run deterministic swing scans, review ranked research
            candidates, and attach catalyst context from persisted or manual notes.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge value={`${data.universes.length} universes`} tone="info" />
          <Badge value={`${data.candidates.length} candidates`} tone="good" />
          <Badge value={data.workspace?.name || "No workspace"} tone={data.workspace ? "info" : "warning"} />
        </div>
      </div>
      <p className="mt-4 text-xs text-slate-500">Last refreshed {formatDateTime(data.lastUpdatedAt)}</p>
    </section>
  );
}
