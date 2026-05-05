import { MetricCard } from "@/components/layout/panel";
import { StatGrid } from "@/components/ui/StatGrid";
import type { WorkspaceBrief } from "@/lib/brief/types";
import { formatInteger } from "@/lib/formatting/numbers";

export function BriefSummaryCards({ brief }: { brief: WorkspaceBrief }) {
  return (
    <StatGrid>
      <MetricCard label="Symbols reviewed" value={formatInteger(brief.summary.totalSymbolsReviewed)} detail="Brief focus rows" />
      <MetricCard label="Fresh symbols" value={formatInteger(brief.summary.freshSymbols)} detail="Market memory state" />
      <MetricCard label="Stale/degraded" value={formatInteger(brief.summary.staleOrDegradedSymbols)} detail="Review recommended" />
      <MetricCard label="Active setups" value={formatInteger(brief.summary.activeSetupCount)} detail="Setup context" />
      <MetricCard label="Review needed" value={formatInteger(brief.summary.reviewRecommendedCount)} detail="Open evidence issues" />
      <MetricCard label="Outcome updates" value={formatInteger(brief.summary.recentOutcomeUpdateCount)} detail="Observed horizons" />
      <MetricCard label="Pending actions" value={formatInteger(brief.summary.pendingBackendActionCount)} detail="Backend items" />
    </StatGrid>
  );
}
