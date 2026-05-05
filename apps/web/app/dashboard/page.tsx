import { AvoidConditions } from "@/components/dashboard/avoid-conditions";
import { BackendStatePanel } from "@/components/dashboard/backend-state-panel";
import { FollowUpPanel } from "@/components/dashboard/follow-up-panel";
import { MarketBoard } from "@/components/dashboard/market-board";
import { SignalFocusPanel } from "@/components/dashboard/signal-focus-panel";
import { SignalDigestPanel } from "@/components/dashboard/signal-digest-panel";
import { TopSummaryRail } from "@/components/dashboard/top-summary-rail";
import { WatchlistPanel } from "@/components/dashboard/watchlist-panel";
import { EmptyState } from "@/components/empty-states/empty-state";
import { AppShell } from "@/components/layout/app-shell";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Metric } from "@/components/ui/Metric";
import { PageHeader } from "@/components/ui/PageHeader";
import { getDashboardData } from "@/lib/api/dashboard";

type DashboardPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
    signalId?: string;
  }>;
};

export default async function DashboardPage({ searchParams }: DashboardPageProps) {
  const params = await searchParams;
  const data = await getDashboardData(params);

  return (
    <AppShell appName={data.appName}>
      <div className="space-y-6">
        <PageHeader
          eyebrow="Operator cockpit"
          title="Daily market intelligence"
          description="Read-only deterministic analysis across watchlists, signals, context, outcomes, and backend follow-up items."
          actions={
            <>
            <Metric label="Workspace" value={data.workspace?.name || "Not selected"} />
            <WorkflowLinks workspaceId={data.workspace?.id} targets={["commandCenter", "brief", "triage", "scanner", "dataOnboarding", "preferences", "review", "journal"]} />
          </>
          }
        />
        {!data.workspace && (
          <EmptyState
            title="No workspace available"
            message="Seed or create a workspace in the API before workspace-scoped dashboard sections can load."
          />
        )}
        <TopSummaryRail data={data} />
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-6">
            <MarketBoard data={data} />
            <SignalFocusPanel data={data} />
          </div>
          <div className="space-y-6">
            <AvoidConditions data={data} />
            <SignalDigestPanel data={data} />
            <WatchlistPanel data={data} />
            <FollowUpPanel data={data} />
          </div>
        </div>
        <BackendStatePanel data={data} />
      </div>
    </AppShell>
  );
}
