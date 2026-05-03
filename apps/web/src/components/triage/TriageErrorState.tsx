import { Badge } from "@/components/status/badge";
import type { TriageFailure } from "@/lib/triage/types";

export function TriageErrorState({ failures }: { failures: TriageFailure[] }) {
  if (failures.length === 0) {
    return null;
  }

  return (
    <section className="surface rounded-lg p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Partial backend context</p>
          <h2 className="mt-1 text-lg font-semibold text-[var(--strong)]">Some optional context did not load</h2>
        </div>
        <Badge value={`${failures.length} issue${failures.length === 1 ? "" : "s"}`} tone="warning" />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {failures.slice(0, 6).map((failure) => (
          <div key={`${failure.label}-${failure.status}-${failure.message}`} className="muted-surface rounded-lg p-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge value={failure.missing ? "Unavailable" : `HTTP ${failure.status || "network"}`} tone="warning" />
              <span className="text-sm font-semibold text-[var(--strong)]">{failure.label}</span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{failure.message}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
