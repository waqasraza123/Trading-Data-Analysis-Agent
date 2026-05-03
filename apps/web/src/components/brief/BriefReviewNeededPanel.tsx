import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { WorkspaceBrief } from "@/lib/brief/types";
import { BriefEmptyState } from "./BriefEmptyState";

export function BriefReviewNeededPanel({ brief }: { brief: WorkspaceBrief }) {
  return (
    <Panel title="Review Needed" eyebrow="Open review queue">
      {brief.reviewNeeded.length === 0 ? (
        <BriefEmptyState
          status={brief.sectionStatuses.reviewNeeded}
          fallbackTitle="No review-needed items"
          fallbackMessage="No open operator review or decision-readiness items were returned."
        />
      ) : (
        <div className="space-y-3">
          {brief.reviewNeeded.map((item) => (
            <div key={item.id} className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-[var(--strong)]">{item.label}</h3>
                  <p className="mt-1 text-sm text-slate-500">{item.source}</p>
                </div>
                <Badge value={item.priority} tone={toneForQuality(item.priority)} />
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.reason}</p>
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
