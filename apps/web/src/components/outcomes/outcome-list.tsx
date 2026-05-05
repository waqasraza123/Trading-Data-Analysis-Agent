import { EmptyState } from "@/components/empty-states/empty-state";
import { Badge, toneForQuality } from "@/components/status/badge";
import { OutcomeLabelBadge } from "@/components/status/OutcomeLabelBadge";
import type { SignalOutcome } from "@/lib/api/types";
import { formatDateTime } from "@/lib/formatting/dates";

export function OutcomeList({ outcomes }: { outcomes: SignalOutcome[] }) {
  if (outcomes.length === 0) {
    return <EmptyState title="No outcome history" message="Outcome evaluation has not returned rows for this signal." />;
  }

  return (
    <div className="overflow-hidden rounded-lg border border-[var(--line)]">
      <div className="grid grid-cols-4 bg-[var(--panel-muted)] px-4 py-3 text-xs font-semibold uppercase text-slate-500">
        <span>Horizon</span>
        <span>Status</span>
        <span>Observation</span>
        <span>Window end</span>
      </div>
      {outcomes.map((outcome) => (
        <div key={outcome.id} className="grid grid-cols-4 gap-3 border-t border-[var(--line)] px-4 py-3 text-sm">
          <span className="font-medium">{outcome.horizon_minutes}m</span>
          <Badge value={outcome.evaluation_status} tone={toneForQuality(outcome.evaluation_status)} />
          <OutcomeLabelBadge value={outcome.outcome_label} />
          <span className="text-slate-500">{formatDateTime(outcome.future_window_end)}</span>
        </div>
      ))}
    </div>
  );
}
