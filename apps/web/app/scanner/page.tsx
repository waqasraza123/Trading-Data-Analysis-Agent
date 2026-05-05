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
      <div className="space-y-6">
        <ScannerHero data={data} />
        {!data.workspace && (
          <ScannerEmptyState
            title="No workspace available"
            message="Seed or create a workspace before scanner controls can create watchlists or scheduled scans."
          />
        )}
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_420px]">
          <div className="space-y-6">
            <ScannerPresetGallery data={data} />
            <WatchlistManager data={data} />
            <ScanConfigForm data={data} />
            <RunScanNowPanel data={data} />
            <ScanConfigList data={data} />
          </div>
          <div className="space-y-6">
            <DailyWorkflowPanel
              workspaceId={data.workspace?.id || null}
              watchlistId={data.watchlists[0]?.watchlist.id || null}
              runs={data.dailyWorkflowRuns}
              selectedRun={data.selectedDailyWorkflowRun}
              selectedSteps={data.selectedDailyWorkflowSteps}
              basePath="/scanner"
            />
            <ScanRunHistory data={data} />
            <ScanRunDetail data={data} />
          </div>
        </div>
        <ScanResultSignalList data={data} />
        <ScannerErrorState failures={data.failures} />
      </div>
    </AppShell>
  );
}
