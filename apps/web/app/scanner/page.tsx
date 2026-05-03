import { AppShell } from "@/components/layout/app-shell";
import { ScanConfigForm } from "@/components/scanner/ScanConfigForm";
import { ScanConfigList } from "@/components/scanner/ScanConfigList";
import { ScanResultSignalList } from "@/components/scanner/ScanResultSignalList";
import { ScanRunDetail } from "@/components/scanner/ScanRunDetail";
import { ScanRunHistory } from "@/components/scanner/ScanRunHistory";
import { ScannerEmptyState } from "@/components/scanner/ScannerEmptyState";
import { ScannerErrorState } from "@/components/scanner/ScannerErrorState";
import { ScannerHeader } from "@/components/scanner/ScannerHeader";
import { ScannerPresetGallery } from "@/components/scanner/ScannerPresetGallery";
import { ScannerStatusPanel } from "@/components/scanner/ScannerStatusPanel";
import { WatchlistManager } from "@/components/scanner/WatchlistManager";
import { getScannerData } from "@/lib/api/scanner";

type ScannerPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
    runId?: string;
  }>;
};

export default async function ScannerPage({ searchParams }: ScannerPageProps) {
  const params = await searchParams;
  const data = await getScannerData(params);

  return (
    <AppShell appName={data.appName}>
      <div className="space-y-6">
        <ScannerHeader data={data} />
        {!data.workspace && (
          <ScannerEmptyState
            title="No workspace available"
            message="Seed or create a workspace before scanner controls can create watchlists or scheduled scans."
          />
        )}
        <ScannerStatusPanel data={data} />
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_420px]">
          <div className="space-y-6">
            <ScannerPresetGallery data={data} />
            <WatchlistManager data={data} />
            <ScanConfigForm data={data} />
            <ScanConfigList data={data} />
          </div>
          <div className="space-y-6">
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
