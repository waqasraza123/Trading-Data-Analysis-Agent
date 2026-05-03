import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { WorkspaceBrief } from "@/lib/brief/types";
import { BriefEmptyState } from "./BriefEmptyState";

export function BriefWatchNextPanel({ brief }: { brief: WorkspaceBrief }) {
  return (
    <Panel title="Watch Next" eyebrow="Observations">
      {brief.watchNext.length === 0 ? (
        <BriefEmptyState
          status={brief.sectionStatuses.watchNext}
          fallbackTitle="No watch-next observations"
          fallbackMessage="Setup context did not return next observations or observation zones."
        />
      ) : (
        <div className="space-y-3">
          {brief.watchNext.map((item) => (
            <div key={item.id} className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-[var(--strong)]">
                    {item.symbol} {item.timeframe}
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">{item.sourceArtifact}</p>
                </div>
                <Badge value="Observation zone" tone="info" />
              </div>
              <p className="mt-3 text-sm font-medium text-[var(--strong)]">{item.observation}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.reason}</p>
              {item.signalId && (
                <Link className="mt-3 inline-flex text-xs font-medium text-slate-500 hover:text-[var(--strong)]" href={`/signals/${item.signalId}`}>
                  Review signal
                </Link>
              )}
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
