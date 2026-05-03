import { MetricCard } from "@/components/layout/panel";
import type { QualityScoreboardData } from "@/lib/quality/types";
import { formatNumber } from "@/lib/quality/labels";

export function QualitySummaryCards({ data }: { data: QualityScoreboardData }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <MetricCard label="Profiles with strong observed follow-through" value={formatNumber(data.summary.strongObservedFollowThrough)} detail="Profile cohorts above the configured review threshold." />
      <MetricCard label="Profiles needing review" value={formatNumber(data.summary.profilesNeedingReview)} detail="Diagnostic labels or recommendations returned." />
      <MetricCard label="Patterns with elevated reversal" value={formatNumber(data.summary.elevatedReversalPatterns)} detail="Pattern cohorts with higher reversal behavior." />
      <MetricCard label="Symbols/timeframes degraded" value={formatNumber(data.summary.degradedSymbolTimeframes)} detail="Symbol cohorts with degraded behavior or coverage warnings." />
      <MetricCard label="Confidence calibration warnings" value={formatNumber(data.summary.confidenceCalibrationWarnings)} detail="Overconfidence or underconfidence labels." />
      <MetricCard label="Drift detected" value={formatNumber(data.summary.driftDetected)} detail="Recent cohorts changed versus baseline." />
    </div>
  );
}
