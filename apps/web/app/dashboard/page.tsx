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
import { getDashboardData } from "@/lib/api/dashboard";
import Link from "next/link";

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
        <section className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-slate-500">Operator cockpit</p>
            <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">Daily market intelligence</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
              Read-only deterministic analysis across watchlists, signals, context, outcomes, and backend follow-up items.
            </p>
          </div>
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-sm text-slate-500">
            Workspace {data.workspace?.name || "not selected"}
          </div>
          <Link
            className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-900"
            href={`/triage${data.workspace ? `?workspaceId=${data.workspace.id}` : ""}`}
          >
            Open triage board
          </Link>
        </section>
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
