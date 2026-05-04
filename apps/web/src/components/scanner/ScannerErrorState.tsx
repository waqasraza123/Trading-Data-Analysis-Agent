import { Badge } from "@/components/status/badge";
import type { ScannerFailure } from "@/lib/scanner/types";

type ScannerErrorStateProps = {
  failures: ScannerFailure[];
};

export function ScannerErrorState({ failures }: ScannerErrorStateProps) {
  if (failures.length === 0) {
    return null;
  }

  return (
    <section className="surface rounded-lg p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Backend state</p>
          <h2 className="mt-1 text-lg font-semibold text-[var(--strong)]">Unavailable scanner data</h2>
        </div>
        <Badge value={`${failures.length} issue${failures.length === 1 ? "" : "s"}`} tone="warning" />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {failures.map((failure) => (
          <div key={`${failure.label}-${failure.status}-${failure.message}`} className="muted-surface rounded-lg p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <h3 className="text-sm font-semibold text-[var(--strong)]">{failure.label}</h3>
              <Badge value={failure.missing ? "Optional endpoint missing" : `HTTP ${failure.status}`} tone={failure.missing ? "warning" : "danger"} />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-500">{failure.message}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
