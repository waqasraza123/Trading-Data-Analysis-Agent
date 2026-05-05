import { MetricCard } from "@/components/layout/panel";
import { StatGrid } from "@/components/ui/StatGrid";
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
  const scopedCount = data.allCandidates.length;
  const profileDetail = data.selectedPreferenceProfile
    ? `${data.selectedPreferenceProfile.name} scope`
    : "All profiles";

  return (
    <section className="space-y-3">
      <StatGrid>
        <MetricCard label="Visible setups" value={formatInteger(visibleCount)} detail="After filters" />
        <MetricCard label="Preference scope" value={formatInteger(scopedCount)} detail={profileDetail} />
        <MetricCard label="Review required" value={formatInteger(counts.get("review_required") || 0)} detail="Manual attention" />
        <MetricCard label="Needs confirmation" value={formatInteger(counts.get("needs_confirmation") || 0)} detail="Wait for context" />
        <MetricCard label="Conflicted" value={formatInteger(counts.get("conflicted") || 0)} detail="Mixed evidence" />
        <MetricCard label="Fresh setups" value={formatInteger(freshCount)} detail="Market memory" />
        <MetricCard label="Unscoped setups" value={formatInteger(data.unfilteredCandidateCount)} detail="Before preferences" />
      </StatGrid>
      <p className="text-xs text-slate-500">
        Last loaded {formatDateTime(data.lastLoadedAt)}. Missing optional context {formatInteger(missingContextCount)}.
      </p>
    </section>
  );
}
