import { AppShell } from "@/components/layout/AppShell";

export function BriefSkeleton() {
  return (
    <AppShell appName="Daily Trading Dashboard">
      <div className="space-y-6">
        <div className="h-80 animate-pulse rounded-3xl border border-white/70 bg-slate-100 shadow-[0_30px_100px_rgba(15,23,42,0.08)] dark:border-slate-800 dark:bg-slate-900" />
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)]">
          <div className="space-y-6">
            <div className="h-96 animate-pulse rounded-3xl bg-slate-100 dark:bg-slate-900" />
            <div className="h-80 animate-pulse rounded-3xl bg-slate-100 dark:bg-slate-900" />
          </div>
          <div className="space-y-6">
            <div className="h-72 animate-pulse rounded-3xl bg-slate-100 dark:bg-slate-900" />
            <div className="h-72 animate-pulse rounded-3xl bg-slate-100 dark:bg-slate-900" />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
