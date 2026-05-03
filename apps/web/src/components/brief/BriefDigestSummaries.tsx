import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { WorkspaceBrief } from "@/lib/brief/types";
import { humanizeLabel } from "@/lib/formatting/labels";
import { BriefEmptyState } from "./BriefEmptyState";

export function BriefDigestSummaries({ brief }: { brief: WorkspaceBrief }) {
  return (
    <Panel title="Digest Summaries" eyebrow="Recent compiled context">
      {brief.digestSummaries.length === 0 ? (
        <BriefEmptyState
          status={brief.sectionStatuses.digests}
          fallbackTitle="No digest summaries"
          fallbackMessage="No recent signal digest items were returned."
        />
      ) : (
        <div className="space-y-3">
          {brief.digestSummaries.map((digest) => (
            <div key={digest.id} className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <h3 className="font-semibold text-[var(--strong)]">{digest.title}</h3>
                <Badge value={digest.priority} tone={toneForQuality(digest.priority)} />
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{digest.summary}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge value={humanizeLabel(digest.itemType)} tone="info" />
                {digest.signalId && (
                  <Link className="text-xs font-medium text-slate-500 hover:text-[var(--strong)]" href={`/signals/${digest.signalId}`}>
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
