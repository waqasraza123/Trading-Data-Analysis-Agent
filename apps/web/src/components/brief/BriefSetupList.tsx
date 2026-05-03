import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge, toneForBias, toneForQuality } from "@/components/status/badge";
import type { WorkspaceBrief } from "@/lib/brief/types";
import { humanizeLabel } from "@/lib/formatting/labels";
import { BriefEmptyState } from "./BriefEmptyState";

export function BriefSetupList({ brief }: { brief: WorkspaceBrief }) {
  return (
    <Panel title="Active Setups" eyebrow="Setup context">
      {brief.activeSetups.length === 0 ? (
        <BriefEmptyState
          status={brief.sectionStatuses.activeSetups}
          fallbackTitle="No active setups"
          fallbackMessage="No directional setup context was available in the current brief."
        />
      ) : (
        <div className="space-y-3">
          {brief.activeSetups.map((setup) => (
            <article key={setup.signalId} className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-[var(--strong)]">
                    {setup.symbol} {setup.timeframe}
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">{humanizeLabel(setup.patternType)}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge value={setup.bias} tone={toneForBias(setup.bias)} />
                  <Badge value={setup.confidenceLabel} tone={toneForQuality(setup.confidenceLabel)} />
                  <Badge value={setup.setupQualityLabel} tone={toneForQuality(setup.setupQualityLabel)} />
                </div>
              </div>
              {setup.keyEvidence.length > 0 && (
                <ul className="mt-4 space-y-2">
                  {setup.keyEvidence.map((evidence) => (
                    <li key={evidence} className="text-sm leading-6 text-slate-600 dark:text-slate-300">
                      {evidence}
                    </li>
                  ))}
                </ul>
              )}
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <Detail label="Invalidation context" value={setup.invalidationContext || "Not available"} />
                <Detail label="Wait condition" value={setup.waitCondition || "Not available"} />
              </dl>
              <Link
                className="mt-4 inline-flex rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium hover:bg-white dark:hover:bg-slate-900"
                href={setup.reviewLink}
              >
                Review signal
              </Link>
            </article>
          ))}
        </div>
      )}
    </Panel>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 font-medium text-[var(--strong)]">{value}</dd>
    </div>
  );
}
