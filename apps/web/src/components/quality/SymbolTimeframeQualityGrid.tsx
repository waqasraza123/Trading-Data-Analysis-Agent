import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { formatPercent, qualityLabel, qualityTone } from "@/lib/quality/labels";
import type { QualityScoreboardData } from "@/lib/quality/types";

export function SymbolTimeframeQualityGrid({ data }: { data: QualityScoreboardData }) {
  if (data.symbolTimeframeRows.length === 0) {
    return null;
  }
  return (
    <Panel title="Symbol/timeframe quality" eyebrow="Observed behavior grid">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.symbolTimeframeRows.map((row) => (
          <div key={row.id} className="muted-surface rounded-lg p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-[var(--strong)]">{row.symbol}</h3>
                <p className="mt-1 text-xs text-slate-500">{row.timeframe} · {row.sampleSize} sample size</p>
              </div>
              <Badge value={qualityLabel(row.diagnosticLabel)} tone={qualityTone(row.diagnosticLabel)} />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <Metric label="Observed follow-through" value={formatPercent(row.observedFollowThrough)} />
              <Metric label="Reversal" value={formatPercent(row.reversalRate)} />
              <Metric label="Data quality" value={row.dataQuality} />
              <Metric label="Sample size" value={String(row.sampleSize)} />
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}
