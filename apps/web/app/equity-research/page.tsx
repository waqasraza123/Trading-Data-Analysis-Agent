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
import { AnimatedSection } from "@/components/ui/motion";
import { getEquityResearchData } from "@/lib/api/equityResearch";

type EquityResearchPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
    universeId?: string;
    scanRunId?: string;
    candidateId?: string;
  }>;
};

export default async function EquityResearchPage({ searchParams }: EquityResearchPageProps) {
  const params = await searchParams;
  const data = await getEquityResearchData(params);

  return (
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <AnimatedSection as="section" className="space-y-6">
        <EquityResearchHeader data={data} />
        {!data.workspace && (
          <EquityResearchEmptyState
            title="No workspace available"
            message="Seed or create a workspace before equity research universes and scan runs can be created."
          />
        )}
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_440px]">
          <div className="space-y-6">
            <EquityDataReadinessPanel data={data} />
            <EquityDataProviderPanel data={data} />
            <EquityUniversePanel data={data} />
            <EquityUniverseImportPanel data={data} />
            <EquityUniverseFileImportPanel data={data} />
            <EquityUniverseMembers data={data} />
            <SwingScanForm data={data} />
            <SwingCandidateTable data={data} />
          </div>
          <div className="space-y-6">
            <EquityDataOperationsPanel data={data} />
            <EquityEnrichmentJobsPanel data={data} />
            <SwingCandidateDetail data={data} />
            <EquityMetadataPanel data={data} />
            <EquityFundamentalsPanel data={data} />
            <EquityEarningsPanel data={data} />
            <CatalystContextPanel data={data} />
            <EquityProviderRequestHistory data={data} />
          </div>
        </div>
        <EquityResearchErrorState failures={data.failures} />
      </AnimatedSection>
    </AppShell>
  );
}
