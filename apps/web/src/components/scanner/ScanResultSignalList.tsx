import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge, toneForBias, toneForQuality } from "@/components/status/badge";
import { compactSymbolLabel, safeScannerText } from "@/lib/scanner/labels";
import type { ScannerData } from "@/lib/scanner/types";

export function ScanResultSignalList({ data }: { data: ScannerData }) {
  return (
    <Panel title="Scan result signals" eyebrow="Produced by selected run">
      {!data.selectedRun ? (
        <div className="muted-surface rounded-lg p-5 text-sm text-slate-500">Run a scan or open a returned scan run to review produced signals.</div>
      ) : data.selectedRunSignals.length === 0 ? (
        <div className="muted-surface rounded-lg p-5 text-sm text-slate-500">No signal records were returned for this scan run.</div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.selectedRunSignals.map((classification) => {
            const signal = classification.signal;
            const dataQuality = classification.confidence_components.find((component) => component.component_name === "data_quality");
            return (
              <div key={signal.id} className="muted-surface rounded-lg p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-[var(--strong)]">{compactSymbolLabel(data.symbols, signal.symbol_id)} {signal.timeframe}</h3>
                    <p className="mt-1 text-sm text-slate-500">{safeScannerText(signal.summary)}</p>
                  </div>
                  <Badge value={signal.bias} tone={toneForBias(signal.bias)} />
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Badge value={signal.confidence_label} tone={toneForQuality(signal.confidence_label)} />
                  <Badge value={signal.pattern_type || "No pattern"} tone="info" />
                  <Badge value={dataQuality ? `Data quality ${dataQuality.component_score}` : "Data quality not available"} tone="neutral" />
                </div>
                <div className="mt-4 flex flex-wrap gap-3 text-sm font-medium">
                  <Link className="text-[var(--info)]" href={`/signals/${signal.id}`}>Review result</Link>
                  <Link className="text-[var(--info)]" href={`/signals/${signal.id}#setup-context`}>Setup context</Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}
