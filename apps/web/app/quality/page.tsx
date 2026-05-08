import { AppShell } from "@/components/layout/AppShell";
import { CohortDriftPanel } from "@/components/quality/CohortDriftPanel";
import { ConfidenceCalibrationPanel } from "@/components/quality/ConfidenceCalibrationPanel";
import { PatternAttributionPanel } from "@/components/quality/PatternAttributionPanel";
import { ProfileReliabilityTable } from "@/components/quality/ProfileReliabilityTable";
import { QualityEmptyState } from "@/components/quality/QualityEmptyState";
import { QualityErrorState } from "@/components/quality/QualityErrorState";
import { QualityReviewFocusPanel } from "@/components/quality/QualityReviewFocusPanel";
import { QualityScoreboardHeader } from "@/components/quality/QualityScoreboardHeader";
import { QualitySummaryCards } from "@/components/quality/QualitySummaryCards";
import { QualityWarningsPanel } from "@/components/quality/QualityWarningsPanel";
import { SymbolTimeframeQualityGrid } from "@/components/quality/SymbolTimeframeQualityGrid";
import { WalkForwardPanel } from "@/components/quality/WalkForwardPanel";
import { AnimatedSection } from "@/components/ui/motion";
import { getQualityScoreboardData } from "@/lib/api/quality";

type QualityPageProps = {
  searchParams: Promise<Record<string, string | undefined>>;
};

export default async function QualityPage({ searchParams }: QualityPageProps) {
  const params = await searchParams;
  const data = await getQualityScoreboardData(params);

  return (
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <AnimatedSection as="section" className="space-y-6">
        <QualityScoreboardHeader data={data} />
        <QualityErrorState failures={data.failures} />
        {!data.workspace || !data.hasAnyQualityData ? (
          <QualityEmptyState />
        ) : (
          <>
            <QualitySummaryCards data={data} />
            <QualityReviewFocusPanel data={data} />
            <QualityWarningsPanel data={data} />
            <ProfileReliabilityTable data={data} />
            <PatternAttributionPanel data={data} />
            <ConfidenceCalibrationPanel data={data} />
            <WalkForwardPanel data={data} />
            <CohortDriftPanel data={data} />
            <SymbolTimeframeQualityGrid data={data} />
          </>
        )}
      </AnimatedSection>
    </AppShell>
  );
}
