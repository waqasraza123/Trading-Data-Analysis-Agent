import { AvoidConditions } from "@/components/dashboard/avoid-conditions";
import { BackendStatePanel } from "@/components/dashboard/backend-state-panel";
import { FollowUpPanel } from "@/components/dashboard/follow-up-panel";
import { MarketBoard } from "@/components/dashboard/market-board";
import { SignalFocusPanel } from "@/components/dashboard/signal-focus-panel";
import { SignalDigestPanel } from "@/components/dashboard/signal-digest-panel";
import { TopSummaryRail } from "@/components/dashboard/top-summary-rail";
import { WatchlistPanel } from "@/components/dashboard/watchlist-panel";
import { EmptyState } from "@/components/empty-states/empty-state";
import { AppShell } from "@/components/layout/AppShell";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Metric } from "@/components/ui/Metric";
import { PageHeader } from "@/components/ui/PageHeader";
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";
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
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <AnimatedSection as="section" className="space-y-6">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")}>
          <PageHeader
            eyebrow="Operator cockpit"
            title="Daily market intelligence"
            description="Read-only deterministic analysis across watchlists, signals, context, outcomes, and backend follow-up items."
            actions={
              <>
                <Metric label="Workspace" value={data.workspace?.name || "Not selected"} />
                <WorkflowLinks
                  workspaceId={data.workspace?.id}
                  targets={["commandCenter", "brief", "triage", "scanner", "dataOnboarding", "preferences", "review", "journal"]}
                />
              </>
            }
          />
        </AnimatedListItem>
        {!data.workspace && (
          <AnimatedListItem as="section" style={motionRevealDensityStyle(1, "comfortable")}>
            <EmptyState
              title="No workspace available"
              message="Seed or create a workspace in the API before workspace-scoped dashboard sections can load."
            />
          </AnimatedListItem>
        )}
        {data.workspace && (
          <>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(2, "regular")}>
              <TopSummaryRail data={data} />
            </AnimatedListItem>
            <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_360px]">
              <div className="space-y-6">
                <AnimatedListItem as="section" style={motionRevealDensityStyle(3, "compact")}>
                  <MarketBoard data={data} />
                </AnimatedListItem>
                <AnimatedListItem as="section" style={motionRevealDensityStyle(4, "compact")}>
                  <SignalFocusPanel data={data} />
                </AnimatedListItem>
              </div>
              <div className="space-y-6">
                <AnimatedListItem as="section" style={motionRevealDensityStyle(5, "compact")}>
                  <AvoidConditions data={data} />
                </AnimatedListItem>
                <AnimatedListItem as="section" style={motionRevealDensityStyle(6, "compact")}>
                  <SignalDigestPanel data={data} />
                </AnimatedListItem>
                <AnimatedListItem as="section" style={motionRevealDensityStyle(7, "compact")}>
                  <WatchlistPanel data={data} />
                </AnimatedListItem>
                <AnimatedListItem as="section" style={motionRevealDensityStyle(8, "compact")}>
                  <FollowUpPanel data={data} />
                </AnimatedListItem>
              </div>
            </div>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(9, "regular")}>
              <BackendStatePanel data={data} />
            </AnimatedListItem>
          </>
        )}
      </AnimatedSection>
    </AppShell>
  );
}
