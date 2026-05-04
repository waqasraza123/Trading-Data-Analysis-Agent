import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { WorkspaceBrief } from "@/lib/brief/types";
import { BriefEmptyState } from "./BriefEmptyState";

export function BriefOutcomeUpdates({ brief }: { brief: WorkspaceBrief }) {
  return (
    <Panel title="Outcome Updates" eyebrow="Observed horizons">
      {brief.outcomeUpdates.length === 0 ? (
        <BriefEmptyState
          status={brief.sectionStatuses.outcomeUpdates}
          fallbackTitle="No outcome updates"
          fallbackMessage="No recent observed outcome horizons were returned for current brief signals."
        />
      ) : (
        <div className="space-y-3">
          {brief.outcomeUpdates.map((outcome) => (
            <Link
              key={outcome.id}
              href={`/signals/${outcome.signalId}`}
              className="block rounded-lg border border-[var(--line)] p-4 hover:bg-[var(--panel-muted)]"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-[var(--strong)]">
                    {outcome.symbol} {outcome.timeframe}
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">{outcome.horizon}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge value={outcome.observationLabel} tone={toneForQuality(outcome.observationLabel)} />
                  <Badge value={outcome.outcomeLabel} tone="info" />
                </div>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{outcome.safeSummary}</p>
            </Link>
          ))}
        </div>
      )}
    </Panel>
  );
}
