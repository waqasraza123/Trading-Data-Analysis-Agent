import {
  ReviewMetricGrid,
  ReviewSurfaceMetric,
} from "@/components/review-surfaces/ReviewSurface";
import type { QualityScoreboardData } from "@/lib/quality/types";
import { formatNumber } from "@/lib/quality/labels";

export function QualitySummaryCards({ data }: { data: QualityScoreboardData }) {
  return (
    <ReviewMetricGrid className="xl:grid-cols-3">
      <ReviewSurfaceMetric label="Strong follow-through" value={formatNumber(data.summary.strongObservedFollowThrough)} detail="Profile cohorts above the configured review threshold." tone="good" />
      <ReviewSurfaceMetric label="Profiles needing review" value={formatNumber(data.summary.profilesNeedingReview)} detail="Diagnostic labels or recommendations returned." tone={data.summary.profilesNeedingReview > 0 ? "warning" : "good"} />
      <ReviewSurfaceMetric label="Elevated reversal" value={formatNumber(data.summary.elevatedReversalPatterns)} detail="Pattern cohorts with higher reversal behavior." tone={data.summary.elevatedReversalPatterns > 0 ? "warning" : "neutral"} />
      <ReviewSurfaceMetric label="Degraded scopes" value={formatNumber(data.summary.degradedSymbolTimeframes)} detail="Symbol/timeframe cohorts with coverage warnings." tone={data.summary.degradedSymbolTimeframes > 0 ? "warning" : "good"} />
      <ReviewSurfaceMetric label="Calibration warnings" value={formatNumber(data.summary.confidenceCalibrationWarnings)} detail="Overconfidence or underconfidence labels." tone={data.summary.confidenceCalibrationWarnings > 0 ? "warning" : "good"} />
      <ReviewSurfaceMetric label="Drift detected" value={formatNumber(data.summary.driftDetected)} detail="Recent cohorts changed versus baseline." tone={data.summary.driftDetected > 0 ? "warning" : "good"} />
    </ReviewMetricGrid>
  );
}
