import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { WorkspaceBrief } from "@/lib/brief/types";
import { humanizeLabel } from "@/lib/formatting/labels";
import { BriefEmptyState } from "./BriefEmptyState";

export function BriefAvoidConditions({ brief }: { brief: WorkspaceBrief }) {
  return (
    <Panel title="Avoid Conditions" eyebrow="Review constraints">
      {brief.avoidConditions.length === 0 ? (
        <BriefEmptyState
          status={brief.sectionStatuses.avoidConditions}
          fallbackTitle="No avoid conditions"
          fallbackMessage="No stale, conflicting, low-quality, or unresolved review constraints were returned."
        />
      ) : (
        <div className="space-y-3">
          {brief.avoidConditions.slice(0, 8).map((item) => (
            <div key={item.id} className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-[var(--strong)]">{item.condition}</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    {item.symbol}
                    {item.timeframe ? ` ${item.timeframe}` : ""}
                  </p>
                </div>
                <Badge value={item.severity} tone={toneForQuality(item.severity)} />
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.reason}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge value={humanizeLabel(item.source)} tone="info" />
                {item.signalId && (
                  <Link className="text-xs font-medium text-slate-500 hover:text-[var(--strong)]" href={`/signals/${item.signalId}`}>
                    Review signal
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
