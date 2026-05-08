import { Badge } from "@/components/status/badge";
import type { TriageCandidate, TriageColumnKey } from "@/lib/triage/types";
import { cn } from "@/lib/ui/cn";
import { motionCardClass, motionRevealClass, motionRevealStyle } from "@/lib/ui/motion";
import type { CSSProperties } from "react";
import { SignalTriageCard } from "./SignalTriageCard";

type SignalTriageColumnProps = {
  column: {
    key: TriageColumnKey;
    title: string;
    description: string;
  };
  candidates: TriageCandidate[];
  style?: CSSProperties;
};

export function SignalTriageColumn({ column, candidates, style }: SignalTriageColumnProps) {
  return (
    <section
      style={style}
      className={cn("flex max-h-[calc(100vh-13rem)] min-h-96 min-w-[320px] flex-col rounded-3xl border border-[var(--border)] bg-[color-mix(in_srgb,var(--surface-muted)_88%,transparent)] p-3 shadow-soft", motionRevealClass())}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-[var(--strong)]">{column.title}</h2>
          <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">{column.description}</p>
        </div>
        <Badge value={String(candidates.length)} tone={candidates.length > 0 ? "info" : "neutral"} />
      </div>
      {candidates.length === 0 ? (
        <div className="flex min-h-40 items-center rounded-2xl border border-dashed border-[var(--border)] bg-[var(--surface)]/60 p-4 text-sm leading-6 text-[var(--text-muted)]">
          No setups currently match this review bucket.
        </div>
      ) : (
        <div className="space-y-3 overflow-y-auto pr-1">
          {candidates.map((candidate, index) => (
            <SignalTriageCard
              key={candidate.id}
              candidate={candidate}
              className={motionCardClass}
              style={motionRevealStyle(index, 45)}
            />
          ))}
        </div>
      )}
    </section>
  );
}
