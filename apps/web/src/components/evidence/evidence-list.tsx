import { EmptyState } from "@/components/empty-states/empty-state";
import { Badge } from "@/components/status/badge";
import type { SignalEvidence } from "@/lib/api/types";
import { formatDecimal } from "@/lib/formatting/numbers";

export function EvidenceList({ evidence }: { evidence: SignalEvidence[] }) {
  if (evidence.length === 0) {
    return <EmptyState title="No evidence rows" message="The backend did not return signal evidence for this section." />;
  }

  return (
    <div className="space-y-3">
      {evidence.map((item) => (
        <div key={item.id} className="muted-surface rounded-lg p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge value={item.evidence_type} tone="info" />
            <Badge value={item.direction} />
            <span className="text-xs text-slate-500">Weight {formatDecimal(item.weight)}</span>
          </div>
          <p className="mt-3 text-sm leading-6 text-[var(--strong)]">{item.message}</p>
          {item.numeric_value && <p className="mt-2 text-xs text-slate-500">Value {formatDecimal(item.numeric_value)}</p>}
        </div>
      ))}
    </div>
  );
}
