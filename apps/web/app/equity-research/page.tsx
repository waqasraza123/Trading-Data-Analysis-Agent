import { AppShell } from "@/components/layout/AppShell";
import { CatalystContextPanel } from "@/components/equity-research/CatalystContextPanel";
import { EquityDataProviderPanel } from "@/components/equity-research/EquityDataProviderPanel";
import { EquityDataOperationsPanel } from "@/components/equity-research/EquityDataOperationsPanel";
import { EquityDataReadinessPanel } from "@/components/equity-research/EquityDataReadinessPanel";
import { EquityEnrichmentJobsPanel } from "@/components/equity-research/EquityEnrichmentJobsPanel";
import { EquityEarningsPanel } from "@/components/equity-research/EquityEarningsPanel";
import { EquityFundamentalsPanel } from "@/components/equity-research/EquityFundamentalsPanel";
import { EquityMetadataPanel } from "@/components/equity-research/EquityMetadataPanel";
import { EquityProviderRequestHistory } from "@/components/equity-research/EquityProviderRequestHistory";
import { EquityResearchEmptyState } from "@/components/equity-research/EquityResearchEmptyState";
import { EquityResearchErrorState } from "@/components/equity-research/EquityResearchErrorState";
import { EquityResearchHeader } from "@/components/equity-research/EquityResearchHeader";
import { EquityUniverseMembers } from "@/components/equity-research/EquityUniverseMembers";
import { EquityUniverseFileImportPanel } from "@/components/equity-research/EquityUniverseFileImportPanel";
import { EquityUniverseImportPanel } from "@/components/equity-research/EquityUniverseImportPanel";
import { EquityUniversePanel } from "@/components/equity-research/EquityUniversePanel";
import { SwingCandidateDetail } from "@/components/equity-research/SwingCandidateDetail";
import { SwingCandidateTable } from "@/components/equity-research/SwingCandidateTable";
import { SwingScanForm } from "@/components/equity-research/SwingScanForm";
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";
import { getEquityResearchData } from "@/lib/api/equityResearch";

type EquityResearchPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
    universeId?: string;
    scanRunId?: string;
    candidateId?: string;
    operationId?: string;
  }>;
};

export default async function EquityResearchPage({ searchParams }: EquityResearchPageProps) {
  const params = await searchParams;
  const data = await getEquityResearchData(params);

  return (
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <AnimatedSection as="section" className="space-y-6">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")}>
          <EquityResearchHeader data={data} />
        </AnimatedListItem>
        {!data.workspace && (
          <AnimatedListItem as="section" style={motionRevealDensityStyle(1, "comfortable")}>
            <EquityResearchEmptyState
              title="No workspace available"
              message="Seed or create a workspace before equity research universes and scan runs can be created."
            />
          </AnimatedListItem>
        )}
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_440px]">
          <div className="space-y-6">
            <AnimatedListItem as="section" style={motionRevealDensityStyle(2, "compact")}>
              <EquityDataReadinessPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(3, "compact")}>
              <EquityDataProviderPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(4, "compact")}>
              <EquityUniversePanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(5, "compact")}>
              <EquityUniverseImportPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(6, "compact")}>
              <EquityUniverseFileImportPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(7, "compact")}>
              <EquityUniverseMembers data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(8, "compact")}>
              <SwingScanForm data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(9, "compact")}>
              <SwingCandidateTable data={data} />
            </AnimatedListItem>
          </div>
          <div className="space-y-6">
            <AnimatedListItem as="section" style={motionRevealDensityStyle(10, "compact")}>
              <EquityDataOperationsPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(11, "compact")}>
              <EquityEnrichmentJobsPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(12, "compact")}>
              <SwingCandidateDetail data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(13, "compact")}>
              <EquityMetadataPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(14, "compact")}>
              <EquityFundamentalsPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(15, "compact")}>
              <EquityEarningsPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(16, "compact")}>
              <CatalystContextPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(17, "compact")}>
              <EquityProviderRequestHistory data={data} />
            </AnimatedListItem>
          </div>
        </div>
        <AnimatedListItem as="section" style={motionRevealDensityStyle(18, "regular")}>
          <EquityResearchErrorState failures={data.failures} />
        </AnimatedListItem>
      </AnimatedSection>
    </AppShell>
  );
}
