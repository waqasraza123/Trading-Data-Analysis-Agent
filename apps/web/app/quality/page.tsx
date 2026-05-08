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
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";
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
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")}>
          <QualityScoreboardHeader data={data} />
        </AnimatedListItem>
        <AnimatedListItem as="section" style={motionRevealDensityStyle(1, "regular")}>
          <QualityErrorState failures={data.failures} />
        </AnimatedListItem>
        {!data.workspace || !data.hasAnyQualityData ? (
          <AnimatedListItem as="section" style={motionRevealDensityStyle(2, "comfortable")}>
            <QualityEmptyState />
          </AnimatedListItem>
        ) : (
          <>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(3, "compact")}>
              <QualitySummaryCards data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(4, "compact")}>
              <QualityReviewFocusPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(5, "compact")}>
              <QualityWarningsPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(6, "compact")}>
              <ProfileReliabilityTable data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(7, "compact")}>
              <PatternAttributionPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(8, "compact")}>
              <ConfidenceCalibrationPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(9, "compact")}>
              <WalkForwardPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(10, "compact")}>
              <CohortDriftPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(11, "compact")}>
              <SymbolTimeframeQualityGrid data={data} />
            </AnimatedListItem>
          </>
        )}
      </AnimatedSection>
    </AppShell>
  );
}
