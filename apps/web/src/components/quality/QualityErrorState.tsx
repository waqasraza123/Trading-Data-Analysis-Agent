import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { QualityFailure } from "@/lib/quality/types";

export function QualityErrorState({ failures }: { failures: QualityFailure[] }) {
  const visibleFailures = failures.filter((failure) => !failure.missing);
  if (visibleFailures.length === 0) {
    return null;
  }
  return (
    <Panel title="Quality data unavailable" eyebrow="API status">
      <div className="space-y-3">
        {visibleFailures.map((failure) => (
          <div key={`${failure.label}-${failure.status}-${failure.message}`} className="muted-surface rounded-lg p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-[var(--strong)]">{failure.label}</h3>
              <Badge value={failure.status ? `HTTP ${failure.status}` : "Network"} tone="warning" />
            </div>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{failure.message}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}
