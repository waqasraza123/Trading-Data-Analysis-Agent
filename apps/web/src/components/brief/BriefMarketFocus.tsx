import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge, toneForBias, toneForQuality } from "@/components/status/badge";
import type { WorkspaceBrief } from "@/lib/brief/types";
import { humanizeLabel } from "@/lib/formatting/labels";
import { BriefEmptyState } from "./BriefEmptyState";

export function BriefMarketFocus({ brief }: { brief: WorkspaceBrief }) {
  return (
    <Panel title="Market Focus" eyebrow="Top symbol/timeframe state">
      {brief.marketFocus.length === 0 ? (
        <BriefEmptyState
          status={brief.sectionStatuses.marketFocus}
          fallbackTitle="No market focus"
          fallbackMessage="Market memory or watchlist state did not return focus rows."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {brief.marketFocus.map((item) => (
            <article key={item.id} className="muted-surface rounded-2xl p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <Link
                    className="text-lg font-semibold text-[var(--strong)] hover:text-[var(--accent)]"
                    href={`/symbols/${item.symbolId}${brief.workspace ? `?workspaceId=${brief.workspace.id}` : ""}`}
                  >
                    {item.symbol}
                  </Link>
                  <p className="mt-1 text-sm text-slate-500">{item.displayName}</p>
                </div>
                <Badge value={item.timeframe} tone="info" />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Badge value={item.latestBias} tone={toneForBias(item.latestBias)} />
                <Badge value={item.confidenceLabel} tone={toneForQuality(item.confidenceLabel)} />
                <Badge value={item.freshnessLabel} tone={toneForQuality(item.freshnessLabel)} />
                <Badge value={item.dataQualityLabel} tone={toneForQuality(item.dataQualityLabel)} />
              </div>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <Detail label="Regime" value={humanizeLabel(item.marketRegimeLabel)} />
                <Detail label="Session" value={humanizeLabel(item.marketSessionLabel)} />
                <Detail label="Setup quality" value={humanizeLabel(item.setupQualityLabel)} />
                <Detail label="Top warning" value={item.topWarning} />
              </dl>
              <div className="mt-4 flex flex-wrap gap-2">
                {item.signalId && (
                  <Link
                    className="premium-control rounded-xl px-3 py-2 text-sm font-semibold"
                    href={`/signals/${item.signalId}`}
                  >
                    Open signal
                  </Link>
                )}
              </div>
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
      <dd className="mt-1 text-sm font-medium text-[var(--strong)]">{value}</dd>
    </div>
  );
}
