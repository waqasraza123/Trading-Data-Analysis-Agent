import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function EquityDataReadinessPanel({ data }: { data: EquityResearchData }) {
  const checks = [
    { label: "Stock universe", ready: data.selectedUniverseMembers.length > 0 },
    { label: "Symbol metadata", ready: Boolean(data.selectedMetadata) },
    { label: "Fundamentals context", ready: Boolean(data.selectedFundamentals) },
    { label: "Earnings context", ready: data.selectedEarnings.length > 0 },
    { label: "Catalyst context", ready: data.catalysts.length > 0 },
  ];
  return (
    <Panel title="Data readiness" eyebrow="Equity research inputs">
      <div className="grid gap-2">
        {checks.map((check) => (
          <div key={check.label} className="flex items-center justify-between rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] px-3 py-2">
            <span className="text-sm font-medium text-[var(--strong)]">{check.label}</span>
            <Badge value={check.ready ? "Enrichment available" : "Enrichment missing"} tone={check.ready ? "good" : "warning"} />
          </div>
        ))}
      </div>
      {data.equityDataFailures.length > 0 && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
          {data.equityDataFailures.length} equity data section(s) reported unavailable state.
        </div>
      )}
    </Panel>
  );
}
