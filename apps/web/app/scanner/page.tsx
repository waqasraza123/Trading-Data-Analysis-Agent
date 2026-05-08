import { AppShell } from "@/components/layout/AppShell";
import { ScanConfigForm } from "@/components/scanner/ScanConfigForm";
import { ScanConfigList } from "@/components/scanner/ScanConfigList";
import { ScanResultSignalList } from "@/components/scanner/ScanResultSignalList";
import { ScanRunDetail } from "@/components/scanner/ScanRunDetail";
import { ScanRunHistory } from "@/components/scanner/ScanRunHistory";
import { ScannerEmptyState } from "@/components/scanner/ScannerEmptyState";
import { ScannerErrorState } from "@/components/scanner/ScannerErrorState";
import { ScannerHero } from "@/components/scanner/ScannerHero";
import { ScannerPresetGallery } from "@/components/scanner/ScannerPresetGallery";
import { WatchlistManager } from "@/components/scanner/WatchlistManager";
import { DailyWorkflowPanel } from "@/components/daily-workflows/DailyWorkflowPanel";
import { RunScanNowPanel } from "@/components/scanner/RunScanNowPanel";
import { getScannerData } from "@/lib/api/scanner";
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";

type ScannerPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
    runId?: string;
    workflowRunId?: string;
  }>;
};

export default async function ScannerPage({ searchParams }: ScannerPageProps) {
  const params = await searchParams;
  const data = await getScannerData(params);

  return (
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <AnimatedSection as="section" className="space-y-6">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")}>
          <ScannerHero data={data} />
        </AnimatedListItem>
        {!data.workspace && (
          <AnimatedListItem as="section" style={motionRevealDensityStyle(1, "comfortable")}>
            <ScannerEmptyState
              title="No workspace available"
              message="Seed or create a workspace before scanner controls can create watchlists or scheduled scans."
            />
          </AnimatedListItem>
        )}
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_420px]">
          <div className="space-y-6">
            <AnimatedListItem as="section" style={motionRevealDensityStyle(2, "compact")}>
              <ScannerPresetGallery data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(3, "compact")}>
              <WatchlistManager data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(4, "compact")}>
              <ScanConfigForm data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(5, "compact")}>
              <RunScanNowPanel data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(6, "compact")}>
              <ScanConfigList data={data} />
            </AnimatedListItem>
          </div>
          <div className="space-y-6">
            <AnimatedListItem as="section" style={motionRevealDensityStyle(7, "compact")}>
              <DailyWorkflowPanel
                workspaceId={data.workspace?.id || null}
                watchlistId={data.watchlists[0]?.watchlist.id || null}
                runs={data.dailyWorkflowRuns}
                selectedRun={data.selectedDailyWorkflowRun}
                selectedSteps={data.selectedDailyWorkflowSteps}
                basePath="/scanner"
              />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(8, "compact")}>
              <ScanRunHistory data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(9, "compact")}>
              <ScanRunDetail data={data} />
            </AnimatedListItem>
          </div>
        </div>
        <AnimatedListItem as="section" style={motionRevealDensityStyle(10, "regular")}>
          <ScanResultSignalList data={data} />
        </AnimatedListItem>
        <AnimatedListItem as="section" style={motionRevealDensityStyle(11, "regular")}>
          <ScannerErrorState failures={data.failures} />
        </AnimatedListItem>
      </AnimatedSection>
    </AppShell>
  );
}
