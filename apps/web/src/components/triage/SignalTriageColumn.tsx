import { Badge } from "@/components/status/badge";
import type { TriageCandidate, TriageColumnKey } from "@/lib/triage/types";
import { SignalTriageCard } from "./SignalTriageCard";

type SignalTriageColumnProps = {
  column: {
    key: TriageColumnKey;
    title: string;
    description: string;
  };
  candidates: TriageCandidate[];
};

export function SignalTriageColumn({ column, candidates }: SignalTriageColumnProps) {
  return (
    <section className="min-h-80 rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-3">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-[var(--strong)]">{column.title}</h2>
          <p className="mt-1 text-xs leading-5 text-slate-500">{column.description}</p>
        </div>
        <Badge value={String(candidates.length)} tone={candidates.length > 0 ? "info" : "neutral"} />
      </div>
      {candidates.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[var(--line)] p-4 text-sm text-slate-500">
          No candidates in this column.
        </div>
      ) : (
        <div className="space-y-3">
          {candidates.map((candidate) => (
            <SignalTriageCard key={candidate.id} candidate={candidate} />
          ))}
        </div>
      )}
    </section>
  );
}
