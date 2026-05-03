import { MetricCard } from "@/components/layout/panel";
import { triageColumns } from "@/lib/triage/labels";
import type { TriageBoardData } from "@/lib/triage/types";
import { formatDateTime } from "@/lib/formatting/dates";
import { formatInteger } from "@/lib/formatting/numbers";

export function TriageSummary({ data }: { data: TriageBoardData }) {
  const counts = new Map(
    triageColumns.map((column) => [
      column.key,
      data.allCandidates.filter((candidate) => candidate.classification.column === column.key).length,
    ]),
  );
  const visibleCount = data.candidates.length;
  const freshCount = data.allCandidates.filter((candidate) => candidate.memory?.freshness_label === "fresh").length;
  const missingContextCount = data.allCandidates.filter((candidate) => candidate.missingContexts.length > 0).length;

  return (
    <section className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Visible candidates" value={formatInteger(visibleCount)} detail="After filters" />
        <MetricCard label="Review required" value={formatInteger(counts.get("review_required") || 0)} detail="Manual attention" />
        <MetricCard label="Needs confirmation" value={formatInteger(counts.get("needs_confirmation") || 0)} detail="Wait for context" />
        <MetricCard label="Conflicted" value={formatInteger(counts.get("conflicted") || 0)} detail="Mixed evidence" />
        <MetricCard label="Fresh candidates" value={formatInteger(freshCount)} detail="Market memory" />
        <MetricCard label="Missing context" value={formatInteger(missingContextCount)} detail="Optional APIs" />
      </div>
      <p className="text-xs text-slate-500">Last loaded {formatDateTime(data.lastLoadedAt)}</p>
    </section>
  );
}
