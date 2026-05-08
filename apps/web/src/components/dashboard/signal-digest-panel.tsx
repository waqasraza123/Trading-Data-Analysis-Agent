import Link from "next/link";
import { EmptyState } from "@/components/empty-states/empty-state";
import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { DashboardData } from "@/lib/api/dashboard";
import { formatDateTime } from "@/lib/formatting/dates";
import { humanizeLabel } from "@/lib/formatting/labels";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle } from "@/lib/ui/motion";

export function SignalDigestPanel({ data }: { data: DashboardData }) {
  const latestDigest = data.signalDigests[0] || null;

  return (
    <Panel title="Signal Digest" eyebrow="Latest compiled context">
      {!latestDigest ? (
        <EmptyState title="No digest available" message="The signal digest endpoint did not return a completed digest." />
      ) : (
        <div className="space-y-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge value={latestDigest.status} tone={toneForQuality(latestDigest.status)} />
              <Badge value={latestDigest.digest_type} tone="info" />
            </div>
            <h3 className="mt-3 font-semibold text-[var(--strong)]">{latestDigest.title}</h3>
            <p className="mt-1 text-xs text-slate-500">Updated {formatDateTime(latestDigest.updated_at)}</p>
          </div>
          {data.latestDigestItems.length ? (
            <div className="space-y-3">
              {data.latestDigestItems.slice(0, 5).map((item, index) => (
                <AnimatedListItem
                  as="article"
                  key={item.id}
                  className={`${motionCardClass} muted-surface rounded-lg p-3`}
                  preset="scale-subtle"
                  style={motionRevealDensityStyle(index, "compact")}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className="text-sm font-semibold text-[var(--strong)]">{item.title}</h4>
                    <Badge value={item.priority} tone={toneForQuality(item.priority)} />
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.summary}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge value={humanizeLabel(item.item_type)} tone="info" />
                    {item.signal_id && (
                      <Link className="text-xs font-medium text-slate-500 hover:text-[var(--strong)]" href={`/signals/${item.signal_id}`}>
                        Open signal
                      </Link>
                    )}
                  </div>
                </AnimatedListItem>
              ))}
            </div>
          ) : (
            <EmptyState title="No digest items" message="The digest returned without item rows." />
          )}
        </div>
      )}
    </Panel>
  );
}
